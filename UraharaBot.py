from ResponseGenerator import ResponseMode, CharacterSettings, AICharacterResponseGenerator
from GeneralCharacterBot import QuarantineSettings, SubRedditSettings, DebugSettings, PostFanartSettings, EmailSettings, CharacterBot

BOTINVOKE_WORDS = ["uraharabot", "urahara bot"] #these words are used to directly invoke the bot
KEY_WORDS = ["urahara","kisuke"] #bot will appear if user mentions these words and comment limit has not been reached
QUOTES_FILENAME = "urahara_quotes.txt"
FACTS_FILENAME = "urahara_facts.txt"
NO_SUBMISSIONS = 30
BOT_TAG = "*beep boop, I'm a bot*"

URAHARA_CHARACTER_SETTINGS = CharacterSettings(
    character_name="Kisuke Urahara from the anime Bleach",
    primary_traits= ["goofy and witty", "comical and clever", "wacky and eccentric", "deriding and taunting", "silly and ridiculous", "snarky and playful"],
    secondary_traits= ["cheerful", "sinister", "mysterious", "dark", "sarcastic", "facetious", "laid-back", "optimistic", "chaotic", "unhinged"],
    response_modes = [
        ResponseMode("Chat", None, 25),
        ResponseMode("Joke", "Respond with a relevant joke", 25),
        ResponseMode("Fact", "Respond with a fun and relevant fact or trivia", 25),
        ResponseMode("SalesPitch", "Respond with a relevant sales pitch", 25)
    ]
)

URAHARA_AI_RESPONSE_GENERATOR = AICharacterResponseGenerator(
    model = "gpt-3.5-turbo",
    character_settings=URAHARA_CHARACTER_SETTINGS,
    max_response_size=210
)

QUARANTINE_SETTINGS = QuarantineSettings(
    blacklisted_words_filename = "blacklist.txt",
    quarantined_users_filename = "quarantined_users.txt",
    quarantine_time = 3600 * 24 * 5
)

SUBREDDITS = [
    SubRedditSettings("bleach", KEY_WORDS, 3, 20),
    SubRedditSettings("TheBleachfolk", KEY_WORDS, 3, 20),
    SubRedditSettings("BleachBraveSouls", KEY_WORDS, 1, 20),
    SubRedditSettings("DefaultSettings", ["Urahara Kisuke", "Kisuke Urahara"],2,20)
]

DEBUG_SETTINGS = DebugSettings(
    debug = False,
    debug_subreddit_settings= SubRedditSettings("uraharaBot", KEY_WORDS + ["testing123"], 3, 5)
)

POST_FANART_SETTINGS = PostFanartSettings(
    posting_subreddit_name="bleach",
    post_frequency = -1,
    fanart_folder= "urahara_art",
    post_title = "Daily Dose of Urahara"
)

EMAIL_SETTINGS = EmailSettings(
    sender_address=None, #replace with your own gmail details
    receiver_address=None,
    password = None,
    email_frequency=3600*4
)

uraharaBot = CharacterBot(
    botinvoke_words= BOTINVOKE_WORDS,
    character_response_generator=URAHARA_AI_RESPONSE_GENERATOR,
    quotes_filename=QUOTES_FILENAME,
    facts_filename=FACTS_FILENAME,
    quarantine_settings=QUARANTINE_SETTINGS,
    subreddits=SUBREDDITS,
    debug_settings=DEBUG_SETTINGS,
    no_submissions=NO_SUBMISSIONS,
    post_fanart_settings=POST_FANART_SETTINGS,
    email_settings=EMAIL_SETTINGS,
    bot_tag=BOT_TAG
)

