#  Pyrogram - Telegram MTProto API Client Library for Python
#  Copyright (C) 2017-present Dan <https://github.com/delivrance>
#
#  This file is part of Pyrogram.
#
#  Pyrogram is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Pyrogram is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with Pyrogram.  If not, see <http://www.gnu.org/licenses/>.

from typing import Union

import pyrogram
from pyrogram import raw
from pyrogram import types
from pyrogram.errors import UserNotParticipant, PeerIdInvalid


class GetChatMember:
    async def get_chat_member(
        self: "pyrogram.Client",
        chat_id: Union[int, str],
        user_id: Union[int, str]
    ) -> "types.ChatMember":
        chat = await self.resolve_peer(chat_id)
        user = await self.resolve_peer(user_id)

        if isinstance(chat, raw.types.InputPeerChat):
            r = await self.invoke(
                raw.functions.messages.GetFullChat(
                    chat_id=chat.chat_id
                )
            )

            members = getattr(r.full_chat.participants, "participants", [])
            users = {i.id: i for i in r.users}

            for member in members:
                member = types.ChatMember._parse(self, member, users, {})

                if isinstance(user, raw.types.InputPeerSelf):
                    if member.user.is_self:
                        return member
                else:
                    if member.user.id == user.user_id:
                        return member
            else:
                raise UserNotParticipant
        elif isinstance(chat, raw.types.InputPeerChannel):
            r = await self.invoke(
                raw.functions.channels.GetParticipant(
                    channel=chat,
                    participant=user
                )
            )

            users = {i.id: i for i in r.users}
            chats = {i.id: i for i in r.chats}

            return types.ChatMember._parse(self, r.participant, users, chats)
        else:
            raise ValueError(f'The chat_id "{chat_id}" belongs to a user')

    async def resolve_peer(
        self: "pyrogram.Client",
        peer_id: Union[int, str]
    ) -> Union[raw.base.InputPeer, raw.base.InputUser, raw.base.InputChannel]:

        if not self.is_connected:
            raise ConnectionError("Client has not been started yet")

        try:
            return await self.storage.get_peer_by_id(peer_id)
        except KeyError:
            if isinstance(peer_id, str):
                if peer_id in ("self", "me"):
                    return raw.types.InputPeerSelf()

                peer_id = re.sub(r"[@+\s]", "", peer_id.lower())

                try:
                    int(peer_id)
                except ValueError:
                    try:
                        return await self.storage.get_peer_by_username(peer_id)
                    except KeyError:
                        await self.invoke(
                            raw.functions.contacts.ResolveUsername(
                                username=peer_id
                            )
                        )
                        return await self.storage.get_peer_by_username(peer_id)
                else:
                    try:
                        return await self.storage.get_peer_by_phone_number(peer_id)
                    except KeyError:
                        raise PeerIdInvalid

            peer_type = utils.get_peer_type(peer_id)

            if peer_type == "user":
                await self.fetch_peers(
                    await self.invoke(
                        raw.functions.users.GetUsers(
                            id=[
                                raw.types.InputUser(
                                    user_id=peer_id,
                                    access_hash=0
                                )
                            ]
                        )
                    )
                )
            elif peer_type == "chat":
                await self.invoke(
                    raw.functions.messages.GetChats(
                        id=[-peer_id]
                    )
                )
            else:
                await self.invoke(
                    raw.functions.channels.GetChannels(
                        id=[
                            raw.types.InputChannel(
                                channel_id=utils.get_channel_id(peer_id),
                                access_hash=0
                            )
                        ]
                    )
                )

            try:
                return await self.storage.get_peer_by_id(peer_id)
            except KeyError:
                return raw.types.InputPeerEmpty()
