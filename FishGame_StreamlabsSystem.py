#!/usr/bin/python
# -*- coding: utf-8 -*-

#---------------------------
# imports
#---------------------------
import codecs
import ctypes
import json
import os
import time
import winsound

import clr
clr.AddReference("IronPython.SQLite.dll")
clr.AddReference("IronPython.Modules.dll")


#---------------------------
# script information
#---------------------------
ScriptName = "Fish Game"
Website = "https://github.com/tmercswims"
Description = "Jak and Daxter fish game."
Creator = "tmerc"
Version = "1.0.0"


#---------------------------
# helper classes
#---------------------------
class Settings(object):
    """Keeps all settings for Fish Game."""

    def __init__(self, settings_file=None):
        try:
            with codecs.open(settings_file, encoding="utf-8-sig", mode="r") as f:
                self.__dict__ = json.load(f, encoding="utf-8")
        except:
            # set defaults
            self.start_command = "!fishgame"
            self.start_permission = "Moderator"
            self.start_message = (
                "Yo we're about to do the fish minigame, guess how many fish I'll have by the end of the 3rd phase of "
                "fish by typing \"{0} <number>\" in chat! Closest guess wins {1}! Exact guess gets VIP until the next "
                "person guesses Exactly Right™ and {2}! If you HIGHLIGHT your guess, and you win, you get {3}x the "
                "rewards! (Recommended guess: 70-100)"
            )

            self.guess_command = "!guess"
            self.guess_duration = 75
            self.guess_nogame_toggle = True
            self.guess_nogame_message = "@{0} There is no active fish game."
            self.guess_toolate_toggle = True
            self.guess_toolate_message = "@{0} Sorry, you must place your guess within {1} seconds."
            self.guess_taken_message = "@{0} Someone else already guessed {1}. Yours has been recorded, but you might want to change it."

            self.end_command = "!endfish"
            self.end_permission = "Moderator"
            self.end_nogame_message = "@{0} There is no active fish game."
            self.end_tie_message = "We have a tie! {0} are {1} off. Rolling for tiebreaker."
            self.end_roll_message = "@{0} rolled a {1}!"
            self.end_winner_message = "The fish game is over, with a phase 3 score of {2}. The winner is @{0}, with a guess of {1}! They have been awarded {3}."
            self.end_vip_message = "@{2}, @{0} just guessed exactly and needs to be given VIP! The previous exact winner who should lose VIP is @{1}."
            self.end_same_vip_message = "@{0} just guessed exactly, but they already have VIP from last time, so we're all good."

            self.reward_nonexact = 200
            self.reward_exact = 400
            self.reward_bonus_multiplier = 3

            self.only_live = False

    def Reload(self, json_data):
        """Replaces all settings with those from the given JSON string."""

        self.__dict__ = json.loads(json_data, encoding="utf-8")

    def Save(self, settings_file):
        """Saves all settings to the given file."""

        try:
            with codecs.open(settings_file, encoding="utf-8-sig", mode="w+") as f:
                json.dump(self.__dict__, f, encoding="utf-8")
            with codecs.open(settings_file.replace("json", "js"), encoding="utf-8-sig", mode="w+") as f:
                f.write("var settings = {0};".format(json.dumps(self.__dict__, encoding='utf-8')))
        except Exception as e:
            winsound.MessageBeep(winsound.MB_ICONHAND)
            ctypes.windll.user32.MessageBoxW(0, "Failed to save settings. Check the script logs for more information.", "Saving Failed", 0)
            Parent.Log(ScriptName, "Failed to save settings to file. " + str(e))

class PreviousVIP(object):
    """Tracks the previous VIP, backed by a file."""

    def __init__(self, file_path):
        self.file_path = file_path
        with codecs.open(file_path, encoding="utf-8-sig", mode="r") as f:
            self._username = f.readline()

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, username):
        self._username = username
        with codecs.open(self.file_path, encoding="utf-8-sig", mode="w+") as f:
            f.write(username)


#---------------------------
# global variables
#---------------------------
global settings_file
settings_file = ""
global settings
settings = Settings()

global entries
entries = dict()
global state
state = 0
global start_time
start_time = 0

global previous_vip_file
previous_vip_file = ""
global previous_vip
previous_vip = None


#---------------------------
# settings functions
#---------------------------
def ReloadSettings(json_data):
    """Reload settings

    Called when a user clicks the "Save Settings" button in the Chatbot UI.
    """

    global settings
    global settings_file

    settings.Reload(json_data)
    settings.Save(settings_file)

def RestoreSettings():
    """Reset settings

    Called when a user clicks the "Restore Default Settings" button in the Chatbot UI.
    """

    global settings
    global settings_file

    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    return_value = ctypes.windll.user32.MessageBoxW(
        0,
        "You are about to restore all settings to their default values. Are you sure you want to continue?",
        "Restore all settings?",
        4
    )

    if return_value == 6:
        settings = Settings()
        settings.Save(settings_file)


#---------------------------
# required functions
#---------------------------
def Init():
    """Initialize data

    Only called on load.
    """

    global settings
    global settings_file
    global previous_vip_file
    global previous_vip

    # load settings
    settings_file = os.path.join(os.path.dirname(__file__), "settings.json")
    settings = Settings(settings_file)

    # load previous vip info
    previous_vip_file = os.path.join(os.path.dirname(__file__), "vip.txt")
    previous_vip = PreviousVIP(previous_vip_file)

def Execute(data):
    """Execute data/process messages"""

    global settings
    global entries
    global state
    global start_time
    global previous_vip

    if settings.only_live and not Parent.IsLive():
        # stop if not live and setting is on
        return

    if data.IsChatMessage() and data.IsFromTwitch():
        # twitch chat message
        if data.GetParam(0).lower() == settings.start_command.lower() and Parent.HasPermission(data.User, settings.start_permission.lower(), ""):
            # start command, with permission
            if state == 1:
                # stop if we are already running
                return

            state = 1
            start_time = int(time.time())
            entries = dict()

            nonexact = "{0} {1}".format(settings.reward_nonexact, Parent.GetCurrencyName())
            exact = "{0} {1}".format(settings.reward_exact, Parent.GetCurrencyName())
            Parent.SendStreamMessage(settings.start_message.format(settings.guess_command, nonexact, exact, settings.reward_bonus_multiplier))
            return

        if data.GetParam(0).lower() == settings.guess_command.lower() and data.GetParamCount() >= 2:
            # guess command
            if state != 1:
                # no active game
                if settings.guess_nogame_toggle:
                    # should send message
                    Parent.SendStreamMessage(settings.guess_nogame_message.format(data.UserName))
                return

            if int(time.time()) - start_time > settings.guess_duration:
                # it's too late
                if settings.guess_toolate_toggle:
                    # should send message
                    Parent.SendStreamMessage(settings.guess_toolate_message.format(data.UserName, settings.guess_duration))
                return

            try:
                # parse guess
                n = int(data.GetParam(1))
            except:
                # silently fail
                return

            is_highlighted = "msg-id=highlighted-message" in data.RawData

            # warn about a duplicate guess
            guesses = [e["guess"] for e in entries.values()]
            if n in guesses:
                Parent.SendStreamMessage(settings.guess_taken_message.format(data.UserName, n))

            # record guess
            entries[data.User] = {
                "data": data,
                "guess": n,
                "bonus": is_highlighted,
                "when": time.time()
            }
            return

        if data.GetParam(0).lower() == settings.end_command.lower():
            # end command
            if data.GetParamCount() < 2:
                # no argument provided
                Parent.SendStreamMessage("@{0} Usage: \"{1} <number>\"".format(data.UserName, settings.end_command))
                return

            try:
                # number of fish
                fish = int(data.GetParam(1))
            except:
                # bad argument
                Parent.SendStreamMessage("@{0} Usage: \"{1} <number>\"".format(data.UserName, settings.end_command))
                return


            if state != 1:
                # no active game
                Parent.SendStreamMessage(settings.end_nogame_message.format(data.UserName))
                return

            # reset state immediately to avoid race condition
            state = 0

            closest_entries = []
            closest_diff = float("inf")

            # find entries that are closest to the real value
            for entry in entries.values():
                diff = abs(fish - entry["guess"])
                if diff < closest_diff:
                    # new solo winner
                    closest_entries = [entry]
                    closest_diff = diff
                elif diff == closest_diff:
                    # tie
                    # find any other closest guess that's the same
                    same_guess = [ce for ce in closest_entries if ce["guess"] == entry["guess"]]


                    if len(same_guess) > 0:
                        # same guess
                        # remove these from the list for now - the winner will go back
                        for g in same_guess:
                            closest_entries.remove(g)

                        # add this new one to the pile
                        same_guess.append(entry)

                        # find the oldest one in the pile
                        first = min(same_guess, key = lambda x: x["when"])

                        # put the oldest one back
                        closest_entries.append(first)

                    else:
                        closest_entries.append(entry)

            if len(closest_entries) == 0:
                # no entries
                return

            if len(closest_entries) == 1:
                # solo winner
                winner = closest_entries[0]
            else:
                # tie
                items = ["@{0}".format(e["data"].UserName) for e in closest_entries]
                st = "{0} and ".format("," if len(items) > 2 else "").join((", ".join(items[:-1]), items[-1]))
                Parent.SendStreamMessage(settings.end_tie_message.format(st, closest_diff))

                while len(closest_entries) > 1:
                    highest_roll = -1
                    highest_entry = None
                    for entry in reversed(closest_entries):
                        # roll for each tying entry
                        roll = Parent.GetRandom(0, 100)
                        Parent.SendStreamMessage(settings.end_roll_message.format(entry["data"].UserName, roll))

                        if roll > highest_roll:
                            highest_roll = roll
                            if highest_entry is not None:
                                closest_entries.remove(highest_entry)
                            highest_entry = entry
                        elif roll < highest_roll:
                            closest_entries.remove(entry)

                winner = closest_entries[0]

            # figure reward
            reward = settings.reward_nonexact
            if closest_diff == 0:
                reward = settings.reward_exact
            if winner["bonus"]:
                reward = reward * settings.reward_bonus_multiplier

            # give reward
            Parent.AddPoints(winner["data"].User, winner["data"].UserName, reward)
            # send basic end message
            Parent.SendStreamMessage(settings.end_winner_message.format(winner["data"].UserName, winner["guess"], fish, "{0} {1}".format(reward, Parent.GetCurrencyName())))

            if closest_diff == 0:
                # send VIP message too
                if winner["data"].UserName == previous_vip.username:
                    # same person guessed exactly again
                    Parent.SendStreamMessage(settings.end_same_vip_message.format(winner["data"].UserName))
                else:
                    # a new person won
                    Parent.SendStreamMessage(settings.end_vip_message.format(winner["data"].UserName, previous_vip.username, Parent.GetChannelName()))
                    previous_vip.username = winner["data"].UserName

            # reset
            state = 0
            start_time = 0
            entries = dict()
            return

def Tick():
    """Tick

    Gets called during every iteration even when there is no incoming data.
    """

    pass


#---------------------------
# optional functions
#---------------------------
def Parse(parse_string, user_id, username, target_id, target_name, message):
    """Parse

    Allows you to create your own custom `$parameter`s.
    """

    return parse_string

def Unload():
    """Unload

    Called when a user reloads their scripts or closes the bot. Cleans up stuff.
    """

    pass

def ScriptToggled(state):
    """ScriptToggled

    Called when a user enables or disables the script.
    """

    pass
