import os
import signal
import json
import discord
from discord import Embed
from discord.ext import tasks
from datetime import datetime, timedelta
from twitchAPI.twitch import Twitch
from dotenv import load_dotenv

with open("config.json", "r") as f:
    data = json.load(f)

current_directory = os.getcwd()
test_directory = os.path.join(current_directory, "test")
live_users = []
stop_program = False

if os.path.isdir(test_directory):
    print("TESTING MODE.")
    load_dotenv(dotenv_path=os.path.join(current_directory, "test/.env"))
    CHANNEL_NUM = int(os.getenv("TEST_CHANNEL"))
    with open("test/test_users.json", "r", errors="ignore") as f:
        test_users = json.load(f)
    for user in test_users:
        # Adds a date time for testing purposes.
        user["started_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+00:00")
    # (datetime.utcnow() - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    live_users = test_users

    print(data)
else:
    print("Production Mode of RugBot is now active.")
    load_dotenv(dotenv_path=os.path.join(current_directory, "prod/.env"))
    CHANNEL_NUM = int(os.getenv("LIVE_CHANNEL"))

print("Config data loaded.")


# Parse as an int or it won't work when passed to client.get_channel()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TWITCH_TOKEN = os.getenv("TWITCH_TOKEN")
TWITCH_CLIENT = os.getenv("TWITCH_CLIENT")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

user_names = ["GenuinelyEuphie", "Simply_Rogue"]
user_dict = {
    user["username"].lower(): {
        "roleid": user["roleid"],
        "message": user["message"],
        "is_live_msg": False,
        "started_at": None,
    }
    for user in data
}
print("User dictionary loaded.")


@tasks.loop(minutes=1)
async def run():
    # Only important for testing purposes.
    if os.path.isdir(test_directory):
        live_users = test_users
    else:
        # Clears the liver_users list on each loop. Otherwise list will not be cleared after use and will keep adding forever.
        live_users = []

    print(f"Loop completed at local time {datetime.now()}")

    twitch = await Twitch(TWITCH_CLIENT, TWITCH_TOKEN)

    # Up to 100 names in the list sent.
    async for user in twitch.get_streams(user_login=user_names):
        print("---Pinged Twitch server.---")
        live_users.append(user.to_dict())

    for e in live_users:
        if datetime.strptime(
            e["started_at"], "%Y-%m-%dT%H:%M:%S+00:00"
        ) >= datetime.utcnow() - timedelta(minutes=10) and (
            not user_dict[e["user_login"]]["is_live_msg"]
            or not e["started_at"] == user_dict[e["user_login"]]["started_at"]
        ):
            print("Message loop run.")
            channel = client.get_channel(CHANNEL_NUM)

            user_dict[e["user_login"]]["started_at"] = e["started_at"]

            embed = Embed(
                title=e["title"],
                url=f"https://twitch.tv/{e['user_login']}",
                description=f"{e['user_name']} is now live on Twitch!",
                timestamp=datetime.now(),
            )
            embed.set_author(
                name=e["user_name"],
                url=f"https://twitch.tv/{e['user_login']}",
                icon_url=user_dict[e["user_login"]]["profile_image"],
            )
            embed.set_thumbnail(
                url=f"https://static-cdn.jtvnw.net/ttv-boxart/{e['game_id']}.jpg"
            )
            if e["user_login"] == "genuinelyeuphie":
                file = discord.File("assets/euphie.png", filename="euphie.png")
                embed.set_image(url="attachment://euphie.png")
            # elif e["user_login"] == "simply_rogue":
            #     file = discord.File(
            #         "assets/rogue-halfbody.png", filename="rogue-halfbody.png"
            #     )
            #     embed.set_image(url="attachment://rogue-halfbody.png")
            else:
                embed.set_image(url=e["thumbnail_url"].format(width=1920, height=1080))
            embed.add_field(name="Playing", value=e["game_name"])
            embed.set_footer(text=f"{e['user_name']} ")

            # Sets message sent to True. This could potentially cause errors because of Discord rates with messages.
            user_dict[e["user_login"]]["is_live_msg"] = True

            # # # # #
            # TODO: TEMPORARY FIX UNTIL FRANK GETS HIS ART.
            # # # # #
            # FRANK NOT HAVING A FILE ERRORS OUT THE CHANNEL SEND.
            if e["user_login"] == "genuinelyeuphie":
                try:
                    await channel.send(
                        content=f"{user_dict[e['user_login']]['message']} <@&{user_dict[e['user_login']]['roleid']}> at https://twitch.tv/{e['user_login']}",
                        file=file,
                        embeds=[embed],
                    )

                # Current measure to catch in case something goes wrong in the main message. This is a backup. I need to setup logging to a file.
                except Exception as err:
                    print(err)
                    await channel.send(
                        content=f"@here {e['user_name']} is live at https://twitch.tv/{e['user_login']}",
                        embeds=[embed],
                    )
            else:
                try:
                    await channel.send(
                        content=f"{user_dict[e['user_login']]['message']} <@&{user_dict[e['user_login']]['roleid']}> at https://twitch.tv/{e['user_login']}",
                        embeds=[embed],
                    )
                # Current measure to catch in case something goes wrong in the main message. This is a backup. I need to setup logging to a file.
                except Exception as err:
                    print(err)
                    await channel.send(
                        content=f"@here {e['user_name']} is live at https://twitch.tv/{e['user_login']}",
                        embeds=[embed],
                    )
        # Resets the message sent to False. TODO: Rethink this when I'm not sleepy. I'm pretty sure this isn't necessary.
        elif datetime.strptime(
            e["started_at"], "%Y-%m-%dT%H:%M:%S+00:00"
        ) < datetime.utcnow() - timedelta(minutes=10):
            user_dict[e["user_login"]]["is_live_msg"] = False


# @tasks.loop(minutes=20)
# async def exit_cleanly():
#     print("20 min loop.")

#     if stop_program:
#         print("20 minutes elapsed.\nProgram Exiting...")
#         exit(0)
#     # elif os.path.isdir(test_directory):
#     #     stop_program = False
#     else:
#         stop_program = True


@client.event
async def on_ready():
    if not run.is_running():
        await get_twitch_user()
        run.start()
        # exit_cleanly.start()
        print("Loop is running.")
    print(f"We have logged in as {client.user}")


async def get_twitch_user():
    twitch = await Twitch(TWITCH_CLIENT, TWITCH_TOKEN)
    async for user in twitch.get_users(logins=user_names):
        # print(user.to_dict())
        user_dict[user.to_dict()["login"]]["profile_image"] = user.to_dict()[
            "profile_image_url"
        ]

    # print(user_dict)


def shutdown(signal_num, frame):
    print("Scheduler stopped.\nProgram Exiting...")
    exit(0)


signal.signal(signal.SIGINT, shutdown)

if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
