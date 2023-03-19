import time
import datetime
import random
import sys
import os
import traceback
import praw

from readwrite_bot import reddit
from ResponseGenerator import AICharacterResponseGenerator

def hasBotCommentedOnPost(submission):
    for top_comment in submission.comments:
        if not hasattr(top_comment.author,"name"):
            continue
        if top_comment.author.name == reddit.user.me().name:
            return True
    return False

def hasBotCommentedOnComment(comment):
    for second_comment in comment.replies:
        if not hasattr(second_comment.author,"name"):
            continue
        if second_comment.author.name == reddit.user.me().name:
            return True
    return False

def hasCommentLimitReached(submission):
    comment_count = 1 if any([keyword in submission.title.lower() for keyword in KEY_WORDS]) else 0
    for top_comment in submission.comments:
        for second_comment in top_comment.replies:
            if not hasattr(second_comment.author,"name"):
                continue
            if not second_comment.author.name == reddit.user.me().name:
                continue
            comment_count += 1
            if comment_count >= COMMENT_LIMIT:
                return True
    return False

def isMentionComment(comment):
    comment_txt = comment.body
    return any([word in comment_txt.lower() for word in BOTINVOKE_WORDS])

def isTextSafe(user_text):
    user_text = "".join(char for char in user_text if char.isalpha() or char in " ")
    for word in ALL_BLACKLISTED:
        if len(word.split()) > 1 and word in user_text.lower():
            return False

        if len(word.split()) == 1 and word in user_text.lower().split():
            return False
    return True

def getAllLines(filename):
    all_lines = []
    with open(filename,mode="r",encoding="utf-8") as read_file:
        lines = read_file.readlines()
        for line in lines:
            all_lines.append(line.rstrip())
        read_file.close()
    return all_lines

def getQuarantinedUsers():
    all_records = getAllLines(QUARANTINED_FILENAME)
    for i in range(len(all_records)-1, -1, -1):
        record = all_records[i].split(",")
        quarantined_date = datetime.datetime.strptime(record[1], "%Y-%m-%d %H:%M:%S.%f")
        quarantine_time_elapsed = (datetime.datetime.now() - quarantined_date).total_seconds()

        if quarantine_time_elapsed > QUARANTINE_TIME:
            all_records.pop(i)
    return all_records

def isUserQuarantined(user):
    quarantined_users = getQuarantinedUsers()
    usernames = [record.split(",")[0] for record in quarantined_users]
    return user.name in usernames

def updateQuarantinedUsers(user = None):
    if user and isUserQuarantined(user):
        return

    quarantined_users = getQuarantinedUsers()
    if user:
        new_record = f"{user.name},{datetime.datetime.now()}"
        quarantined_users.append(new_record)
    with open(QUARANTINED_FILENAME, mode="w", encoding="utf-8") as write_file:
        for record in quarantined_users:
            write_file.write(record + "\n")
        write_file.close()

def postImage():
    account_username = reddit.user.me().name
    for submission in reddit.redditor(account_username).submissions.new(limit = 5):
        date = datetime.datetime.fromtimestamp(submission.created_utc)
        dif = datetime.datetime.utcnow() - date
        if dif < datetime.timedelta(seconds=POST_FREQUENCY):
            return

        supported_img_types = ["png","jpg","jpeg","gif","bmp"]

        post_title = "Daily Dose of Urahara"
        post_id = "a9a69882-6e92-11ec-8100-ce1e12c4bd6a"
        random_image = "./urahara_art/" + random.choice([filename for filename in os.listdir("./urahara_art") if any(filename.endswith(extension) for extension in supported_img_types)])

        if "fanart" in random_image:
            #fanart images must be in the format "fanart#<source>#<nameOfFile>" to be properly credited.
            fanart_credit = random_image.split("#")[1]
            post_title += " (Credit: {})".format(fanart_credit)
            post_id = "a807e9e8-47e2-11ed-bef4-3a6a99e74d02"

        reddit.subreddit(SUBREDDIT_NAME).submit_image(post_title, random_image, flair_id = post_id)
        os.remove(random_image)
        printInfo("Image Post Made, File Removed: " + random_image)
        time.sleep(WAIT_TIME)
        return

def monitorPosts():
    printInfo("Bot monitoring...")
    subreddit = reddit.subreddit(SUBREDDIT_NAME)
    visited = dict()
    updateQuarantinedUsers()
    update_frequency = 3600
    last_update = time.perf_counter()
    start_time = time.perf_counter()

    run_bot = True
    while run_bot:

        for submission in subreddit.new(limit = NO_SUBMISSIONS):
            submission.comments.replace_more(limit=None)
            dividor = "-------------------------------"
            post_title = submission.title
            for key_word in KEY_WORDS:

                if hasattr(submission.author, "name"):
                    if not DEBUG and submission.author.name == reddit.user.me().name:
                        break

                if key_word in post_title.lower() and submission.id not in visited:
                    if not isTextSafe(post_title) or isUserQuarantined(submission.author):
                        addID(submission.id,visited)
                        updateQuarantinedUsers(submission.author)

                        printInfo("=======================================================")
                        printInfo("POST SKIPPED: {}".format(post_title) + "\n")
                        printInfo("=======================================================")

                    elif not hasBotCommentedOnPost(submission):
                        try:
                            response = returnResponse(post_title)
                            submission.reply(response)
                            addID(submission.id,visited)

                            printInfo("=======================================================")
                            printInfo("TITLE: {}".format(post_title) + "\n" + dividor)
                            printInfo("RESPONSE: {}".format(response) + "\n" + dividor)
                            printInfo("=======================================================")
                            time.sleep(WAIT_TIME)

                        except praw.exceptions.APIException as e:
                            printInfo("API Exception, bot resuming in {} secs...".format(WAIT_TIME))
                            time.sleep(WAIT_TIME)

                        except:
                            printInfo("Unexpected Exception, bot resuming in {} secs...".format(WAIT_TIME))
                            traceback.print_exc()
                            time.sleep(WAIT_TIME);

            for top_comment in submission.comments:
                comment_txt = top_comment.body
                if (not isMentionComment(top_comment) and hasCommentLimitReached(submission)):
                    continue

                if hasattr(top_comment.author, "name"):
                    if not DEBUG and top_comment.author.name == reddit.user.me().name:
                        continue

                for key_word in KEY_WORDS:
                    if key_word in comment_txt.lower() and top_comment.id not in visited:
                        if not isTextSafe(comment_txt) or isUserQuarantined(top_comment.author):
                            addID(top_comment.id,visited)
                            updateQuarantinedUsers(top_comment.author)

                            printInfo("=======================================================")
                            printInfo("COMMENT SKIPPED: {}".format(comment_txt) + "\n")
                            printInfo("=======================================================")

                        elif not hasBotCommentedOnComment(top_comment):
                            try:
                                response = returnResponse(comment_txt)
                                top_comment.reply(response)
                                addID(top_comment.id,visited)

                                printInfo("=======================================================")
                                printInfo("COMMENT: {}".format(comment_txt) + "\n" + dividor)
                                printInfo("RESPONSE: {}".format(response) + "\n" + dividor)
                                printInfo("=======================================================")
                                time.sleep(WAIT_TIME)

                            except praw.exceptions.APIException as e:
                                printInfo("API Exception, bot resuming in {} secs...".format(WAIT_TIME))
                                time.sleep(WAIT_TIME)

                            except:
                                printInfo("Unexpected Exception, bot resuming in {} secs...".format(WAIT_TIME))
                                traceback.print_exc()
                                time.sleep(WAIT_TIME);
        if POST_FREQUENCY > 0:
            try:
                postImage()
            except:
                traceback.print_exc()

        time_since_update = time.perf_counter() - last_update
        if time_since_update > update_frequency:
            minutes_elapsed = str(int(time_since_update // 60))
            seconds_elapsed = str(int(time_since_update % 60))
            if len(seconds_elapsed) == 1:
                seconds_elapsed = "0" + seconds_elapsed
            time_str = minutes_elapsed + ":" + seconds_elapsed

            last_update = time.perf_counter()
            visited = dict()
            updateQuarantinedUsers()

            printInfo("Routine Update:")
            printInfo("Comments made over the last {} minutes: {}".format(time_str,len(visited)))

        if RUN_TIME == -1:
            continue
        else:
            curr_time = time.perf_counter()
            time_elapsed = curr_time - start_time
            run_bot = time_elapsed < RUN_TIME


def printInfo(output_str):
    print(output_str)
    sys.stdout.flush()

def addID(id_item,id_dict):
    id_item = str(id_item)
    if id_item in id_dict:
        return
    id_dict[id_item] = 0


def returnResponse(user_text):
    bot_tag = "*beep boop, I'm a bot*"

    bot_reply = ""
    api_call_failed = False
    try:
        AIResponse = AIResponseGenerator.getResponse(user_text)
        bot_reply = AIResponse['choices'][0]['message']['content']

        api_call_failed = AIResponse['choices'][0]['finish_reason'] != 'stop'
    except:
        api_call_failed = True

    reset_chat_history = False
    if api_call_failed:
        reset_chat_history = True
        print("ChatGPT API Call Failed")

    if len(AIResponseGenerator.chat_history) > 16:
        reset_chat_history = True

    if reset_chat_history:
        AIResponseGenerator.resetChatHistory()
        print("ChatGPT History Reset")

    rand_var = random.uniform(0,1)
    if rand_var <= 0.5 and api_call_failed:
        bot_reply = ALL_QUOTES[random.randint(0,len(ALL_QUOTES)-1)]

    if rand_var > 0.5 and api_call_failed:
        bot_reply = ALL_FACTS[random.randint(0,len(ALL_FACTS)-1)]

    response = '{}\n\n{}'.format(bot_reply,bot_tag)
    return response


QUOTES_FILENAME = "urahara_quotes.txt"
FACTS_FILENAME = "urahara_facts.txt"
BLACKLISTED_FILENAME = "blacklist.txt"
QUARANTINED_FILENAME = "quarantined_users.txt"
ALL_QUOTES = getAllLines(QUOTES_FILENAME)
ALL_FACTS =  getAllLines(FACTS_FILENAME)
ALL_BLACKLISTED = getAllLines(BLACKLISTED_FILENAME)
QUARANTINE_TIME = 3600 * 24 * 5
AIResponseGenerator = AICharacterResponseGenerator(model="gpt-3.5-turbo",character="Kisuke Urahara from the anime Bleach", max_response_size=210)


RUN_TIME = -1
SUBREDDIT_NAME = "bleach"
KEY_WORDS = ["urahara","kisuke"]
BOTINVOKE_WORDS = ["uraharabot", "urahara bot"]
NO_SUBMISSIONS = 30
COMMENT_LIMIT = 3
POST_FREQUENCY = -1 #3600 * 24
WAIT_TIME = 10

DEBUG = False #when in debug mode, the bot can reply to its own comments and make replies on its own posts

if __name__ == "__main__":
    """ls = reddit.subreddit("test").flair.templates
    print(ls)
    for submission in reddit.redditor("uraharaBot").submissions.new(limit = 5):
        if submission.title == "The incalculable schemer":
            print(isinstance(submission.link_flair_template_id,str))
            print(submission.link_flair_template_id)
            import pprint
            pprint.pprint(vars(submission))"""
    if DEBUG:
        printInfo("DEBUG MODE STARTED...")
        SUBREDDIT_NAME = "uraharaBot"
        COMMENT_LIMIT = 3
        POST_FREQUENCY = -1 #60 * 2
    monitorPosts()