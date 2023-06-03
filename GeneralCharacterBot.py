import time
import datetime
import random
import sys
import os
import traceback
import praw
import smtplib
import ssl
from email.message import EmailMessage

from readwrite_bot import reddit

class QuarantineSettings:
    def __init__(self, blacklisted_words_filename, quarantined_users_filename, quarantine_time):
        self.blacklisted_words_filename = blacklisted_words_filename
        self.quarantined_users_filename = quarantined_users_filename
        self.quarantine_time = quarantine_time

class SubRedditSettings:
    def __init__(self, name, key_words, top_comment_limit, depth_limit):
        self.name = name
        self.key_words = key_words
        self.top_comment_limit = top_comment_limit
        self.depth_limit = depth_limit

class DebugSettings:
    def __init__(self, debug, debug_subreddit_settings):
        self.debug = debug
        self.debug_subreddit_settings = debug_subreddit_settings

class PostFanartSettings:
    def __init__(self, posting_subreddit_name, post_frequency, fanart_folder, post_title):
        self.posting_subreddit_name = posting_subreddit_name
        self.post_frequency = post_frequency
        self.fanart_folder = fanart_folder
        self.post_title = post_title

class EmailSettings:
    def __init__(self, sender_address, receiver_address, password, email_frequency):
        self.sender_address = sender_address
        self.receiver_address = receiver_address
        self.password = password
        self.email_frequency = email_frequency
        self.last_email_time = None
    
    def sendEmail(self, subject, body):
        if self.last_email_time != None and time.perf_counter() - self.last_email_time < self.email_frequency:
            return

        email_msg = EmailMessage()
        email_msg["From"] = self.sender_address
        email_msg["To"] = self.receiver_address
        email_msg["Subject"] = subject
        email_msg.set_content(body)
        context = ssl.create_default_context()

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                server.login(self.sender_address, self.password)
                server.sendmail(self.sender_address, self.receiver_address, email_msg.as_string())
            self.last_email_time = time.perf_counter();
        except:
            traceback.print_exc()

class PRAWUtilities:
    def __init__(self, subreddits):
        self.subreddits = subreddits
    
    def getSubredditsString(self):
        subreddits_str = ""
        for subreddit in self.subreddits:
            if subreddit.name == "DefaultSettings":
                continue
            subreddits_str += subreddit.name + "+"
        return subreddits_str
    
    def getSubredditSetting(self, item):
        subreddit_setting = [subreddit for subreddit in self.subreddits if subreddit.name == item.subreddit.display_name]
        if len(subreddit_setting) == 0:
            subreddit_setting = [subreddit for subreddit in self.subreddits if subreddit.name == "DefaultSettings"]

        return subreddit_setting[0]

    def extractText(self, item):
        if isinstance(item, praw.models.Submission):
            return item.title
        
        elif isinstance(item, praw.models.Comment):
            return item.body
        
        else:
            raise Exception("Unrecognised object - param must be PRAW Submission or Comment")
    
    def hasBotCommentedOnPost(self, submission):
        for top_comment in submission.comments:
            if not hasattr(top_comment.author,"name"):
                continue
            if top_comment.author.name == reddit.user.me().name:
                return True
        return False
    
    def hasBotCommentedOnComment(self, comment):
        for second_comment in comment.replies:
            if not hasattr(second_comment.author,"name"):
                continue
            if second_comment.author.name == reddit.user.me().name:
                return True
        return False
    
    def hasTopCommentLimitReached(self, submission):
        subreddit_setting = self.getSubredditSetting(submission)
        key_words = subreddit_setting.key_words
        comment_limit = subreddit_setting.top_comment_limit

        comment_count = 1 if any([keyword in submission.title.lower() for keyword in key_words]) else 0
        for top_comment in submission.comments:
            for second_comment in top_comment.replies:
                if not hasattr(second_comment.author,"name"):
                    continue
                if not second_comment.author.name == reddit.user.me().name:
                    continue
                comment_count += 1
                
        return comment_count >= comment_limit
    
    def isBotComment(self, comment, debug):
        if not hasattr(comment.author, "name"):
            return False

        if comment.author.name != reddit.user.me().name:
            return False
        
        if debug:
            return not "user comment" in comment.body
        else:
            return True
    
    def getCommentChain(self, comment):
        current_comment = comment
        comment_chain = []
        while not isinstance(current_comment.parent(), praw.models.Submission):
            comment_chain.insert(0,current_comment)
            current_comment = current_comment.parent()
        comment_chain.insert(0,current_comment)
        return comment_chain


class CharacterBot:
    def __init__(self, botinvoke_words, character_response_generator, quotes_filename, facts_filename, quarantine_settings, subreddits, debug_settings, no_submissions, post_fanart_settings, email_settings, bot_tag):
        self.botinvoke_words = botinvoke_words
        self.character_response_generator = character_response_generator
        self.quotes_filename = quotes_filename
        self.facts_filename = facts_filename 
        self.quarantine_settings = quarantine_settings
        self.subreddits = subreddits 
        self.PRAW_utils = PRAWUtilities(subreddits)
        self.debug_settings = debug_settings
        self.no_submissions = no_submissions
        self.post_fanart_settings = post_fanart_settings
        self.email_settings = email_settings
        self.bot_tag = bot_tag
        self.visited = dict()
        self.update_frequency = 3600
        self.bot_health_threshold = 1

        self.processFiles()
    
    def getAllLines(self, filename):
        all_lines = []
        with open(filename,mode="r",encoding="utf-8") as read_file:
            lines = read_file.readlines()
            for line in lines:
                all_lines.append(line.rstrip())
            read_file.close()
        return all_lines
    
    def printInfo(self, messages_arr):
        dividor = "-" * 50
        for message in messages_arr:
            print(message)
            sys.stdout.flush()
        print(dividor)
        sys.stdout.flush()
    
    def checkBotHealth(self):
        last_comment = reddit.user.me().comments.new(limit=1).__next__()
        days_since_last_comment = datetime.datetime.utcnow() - datetime.datetime.utcfromtimestamp(last_comment.created_utc)
        if days_since_last_comment < datetime.timedelta(days=self.bot_health_threshold):
            return
        
        subject = "Reddit Bot Alert"
        body = f"The Reddit Bot '{reddit.user.me().name}' last commented more than {self.bot_health_threshold} days ago. User intervention may be required."
        self.email_settings.sendEmail(subject, body)
        self.printInfo(["Bot Health Email Sent"])
    
    def processFiles(self):
        self.ALL_QUOTES =  self.getAllLines(self.quotes_filename)
        self.ALL_FACTS = self.getAllLines(self.facts_filename)
        self.ALL_BLACKLISTED_WORDS = self.getAllLines(self.quarantine_settings.blacklisted_words_filename)

        if (not any([filename == self.quarantine_settings.quarantined_users_filename for filename in os.listdir()])):
            with open(self.quarantine_settings.quarantined_users_filename, mode ="w") as write_file:
                write_file.close()
    
    def isCharacterMentionedText(self, item):
        text = self.PRAW_utils.extractText(item).lower()
        subreddit_setting = self.PRAW_utils.getSubredditSetting(item)
        key_words = subreddit_setting.key_words
        return any([word in text.lower() for word in key_words])
    
    def isBotInvokeText(self, item):
        text = self.PRAW_utils.extractText(item).lower()
        return any([word in text.lower() for word in self.botinvoke_words])
    
    def isSafeText(self, item):
        user_text = self.PRAW_utils.extractText(item).lower()
        user_text = "".join(char for char in user_text if char.isalpha() or char in " ")
        for word in self.ALL_BLACKLISTED_WORDS:
            if len(word.split()) > 1 and word in user_text.lower():
                return False

            if len(word.split()) == 1 and word in user_text.lower().split():
                return False
        return True
    
    def shouldRespondToNestedComment(self, nested_comment):
        comment_chain = self.PRAW_utils.getCommentChain(nested_comment)
        if self.PRAW_utils.isBotComment(nested_comment, self.debug_settings.debug):
            return False

        if not self.PRAW_utils.isBotComment(nested_comment.parent(), self.debug_settings.debug):
            return False
        
        subreddit_setting = self.PRAW_utils.getSubredditSetting(nested_comment)
        bot_words = subreddit_setting.key_words + self.botinvoke_words
        question_words = ["who", "what", "why", "how", "where", "did", "do", "tell", "give"] 
        if "?" not in nested_comment.body.lower() and not any([question_word in nested_comment.body.lower().split() for question_word in question_words]) and not any([bot_word in nested_comment.body.lower() for bot_word in bot_words]):
            return False
        
        if len(comment_chain) // 2 > subreddit_setting.depth_limit:
            return False
        else:
            return True
    
    def getQuarantinedUsers(self):
        all_records = self.getAllLines(self.quarantine_settings.quarantined_users_filename)
        for i in range(len(all_records)-1, -1, -1):
            record = all_records[i].split(",")
            quarantined_date = datetime.datetime.strptime(record[1], "%Y-%m-%d %H:%M:%S.%f")
            quarantine_time_elapsed = (datetime.datetime.now() - quarantined_date).total_seconds()

            if quarantine_time_elapsed > self.quarantine_settings.quarantine_time:
                all_records.pop(i)
        return all_records

    def isUserQuarantined(self, user):
        quarantined_users = self.getQuarantinedUsers()
        usernames = [record.split(",")[0] for record in quarantined_users]
        return user.name in usernames

    def updateQuarantinedUsers(self, user = None):
        if user and self.isUserQuarantined(user):
            return

        quarantined_users = self.getQuarantinedUsers()
        if user:
            new_record = f"{user.name},{datetime.datetime.now()}"
            quarantined_users.append(new_record)

        with open(self.quarantine_settings.quarantined_users_filename, mode="w", encoding="utf-8") as write_file:
            for record in quarantined_users:
                write_file.write(record + "\n")
            write_file.close()
    
    def getBotQurantinedUserMessage(self, user):
        quarantined_days = round(self.quarantine_settings.quarantine_time / (3600 * 24), 4)
        bot_reply = f"This message was registered as offensive or inappropriate. u/{user.name} has been banned from using this bot for {quarantined_days} days"
        return bot_reply

    def getBotMessage(self, user_text, chat_history = None):
        bot_reply = ""
        api_call_failed = False
        try:
            AIResponse = self.character_response_generator.getResponse(user_text, chat_history)
            bot_reply = AIResponse['choices'][0]['message']['content']
            api_call_failed = AIResponse['choices'][0]['finish_reason'] != 'stop'
        except:
            api_call_failed = True
            traceback.print_exc()

        reset_chat_history = False
        if api_call_failed:
            reset_chat_history = True
            self.printInfo(["ChatGPT API Call Failed"])

        if len(self.character_response_generator.chat_history) > 12:
            reset_chat_history = True

        if reset_chat_history:
            self.character_response_generator.resetChatHistory()
            self.printInfo(["ChatGPT History Reset"])

        rand_var = random.uniform(0,1)
        if rand_var <= 0.5 and api_call_failed:
            bot_reply = random.choice(self.ALL_QUOTES)

        if rand_var > 0.5 and api_call_failed:
            bot_reply = random.choice(self.ALL_FACTS)
        return bot_reply
    
    def getBotComment(self, item, chat_history = None):
        IsVisited = item.id in self.visited
        if IsVisited and not item.edited:
            return None

        IsNestedComment = isinstance(item, praw.models.Comment) and not isinstance(item.parent(), praw.models.Submission)
        ShouldRespondToNestedComment = IsNestedComment and self.shouldRespondToNestedComment(item)
        if IsNestedComment and not ShouldRespondToNestedComment:
            return None
        
        IsCharacterMentionedText = self.isCharacterMentionedText(item)
        if not IsCharacterMentionedText and not IsNestedComment:
            return None
        
        HasTopCommentLimitReached = isinstance(item, praw.models.Comment) and self.PRAW_utils.hasTopCommentLimitReached(item.submission)
        IsBotInvokeText = self.isBotInvokeText(item)
        if HasTopCommentLimitReached and not IsBotInvokeText and not IsNestedComment:
            return None
        
        IsAuthorMe = hasattr(item.author, "name") and item.author.name == reddit.user.me().name
        if not self.debug_settings.debug and IsAuthorMe:
            return None
        
        HasBotCommentedOnComment = isinstance(item, praw.models.Comment) and self.PRAW_utils.hasBotCommentedOnComment(item)
        if HasBotCommentedOnComment:
            return None
        
        HasBotCommentedOnPost = isinstance(item, praw.models.Submission) and self.PRAW_utils.hasBotCommentedOnPost(item)
        if HasBotCommentedOnPost:
            return None
        
        IsUserQuarantined = hasattr(item.author, "name") and self.isUserQuarantined(item.author)
        if IsUserQuarantined:
            return None
        
        IsSafeText = self.isSafeText(item)
        if not IsSafeText and not IsBotInvokeText and not IsNestedComment:
            return None
        
        if not IsSafeText and (IsBotInvokeText or IsNestedComment):
            self.printInfo(["="*50, f"TEXT SKIPPED: {self.PRAW_utils.extractText(item)}", "="*50])
            self.updateQuarantinedUsers(item.author)
            return self.getBotQurantinedUserMessage(item.author)
        
        bot_reply =  self.getBotMessage(self.PRAW_utils.extractText(item), chat_history)
        bot_comment = '{}\n\n{}'.format(bot_reply,self.bot_tag)
        return bot_comment

    def postImage(self):
        account_username = reddit.user.me().name
        for submission in reddit.redditor(account_username).submissions.new(limit = 5):
            date = datetime.datetime.fromtimestamp(submission.created_utc)
            dif = datetime.datetime.utcnow() - date
            if dif < datetime.timedelta(seconds=self.post_fanart_settings.post_frequency):
                return

            supported_img_types = ["png","jpg","jpeg","gif","bmp"]
            eligible_imgs = [filename for filename in os.listdir(self.post_fanart_settings.fanart_folder) if any(filename.endswith(extension) for extension in supported_img_types)]
            if len(eligible_imgs) == 0:
                return
            post_id = "a9a69882-6e92-11ec-8100-ce1e12c4bd6a"
            random_image = f"./{self.post_fanart_settings.fanart_folder}/" + random.choice(eligible_imgs)

            if "fanart" in random_image:
                #fanart images must be in the format "fanart#<source>#<nameOfFile>" to be properly credited.
                fanart_credit = random_image.split("#")[1]
                post_title += " (Credit: {})".format(fanart_credit)
                post_id = "a807e9e8-47e2-11ed-bef4-3a6a99e74d02"

            reddit.subreddit("r/bleach").submit_image(self.post_fanart_settings.post_title, random_image, flair_id = post_id)
            os.remove(random_image)
            self.printInfo(["Image Post Made, File Removed: " + random_image])
            time.sleep(10)
            return
    
    def postComment(self, bot_comment, item):
        if bot_comment == None:
            if item.id not in self.visited:
                self.visited[item.id] = 0
            return
        try:
            item.reply(bot_comment)
            self.printInfo(["="*50, f"Text: {self.PRAW_utils.extractText(item)}", "="*50, f"Reply: {bot_comment}"])
            self.visited[item.id] = 1
        except:
            self.printInfo([f"Exception Occurred, bot resuming in {60} seconds"])
            traceback.print_exc()
            time.sleep(60)

    def constructChatHistory(self, comments):
        constructed_history = []
        for comment in comments:
            comment_dict = {"role": None, "content": None}
            comment_dict["role"] = "assistant" if self.PRAW_utils.isBotComment(comment, self.debug_settings.debug) else "user"
            comment_content = comment.body.replace("user comment", "").replace(self.bot_tag,"")
            comment_dict["content"] = comment_content
            constructed_history.append(comment_dict)
        return constructed_history
       
    def checkCommentReplies(self, root_comment):
        all_replies = root_comment.replies.list()
        for comment in all_replies:
            comment_chain = self.PRAW_utils.getCommentChain(comment)                            
            chat_history = self.constructChatHistory(comment_chain)
            bot_comment = self.getBotComment(comment, chat_history)
            self.postComment(bot_comment, comment)

    def setUpDebugMode(self):
        self.printInfo(["DEBUG Mode Started..."])
        self.subreddits = self.PRAW_utils.subreddits = [self.debug_settings.debug_subreddit_settings]
        self.update_frequency = 120
        self.email_settings.email_frequency = 120*2
        self.bot_health_threshold = 0.002

    def startBot(self):
        self.printInfo(["Bot monitoring..."])

        if self.debug_settings.debug:
            self.setUpDebugMode()

        self.updateQuarantinedUsers()
        last_update = time.perf_counter()

        print(self.PRAW_utils.getSubredditsString())
        subreddit = reddit.subreddit(self.PRAW_utils.getSubredditsString())
        total_no_submissions = self.no_submissions * (len(self.subreddits)-1)
        while True:
            for submission in subreddit.new(limit = total_no_submissions):
                bot_comment = self.getBotComment(submission)
                self.postComment(bot_comment, submission)

                submission.comments.replace_more(limit=None)
                for top_comment in submission.comments:
                    bot_comment = self.getBotComment(top_comment)
                    self.postComment(bot_comment, top_comment)
                    self.checkCommentReplies(top_comment)
            
            if self.post_fanart_settings.post_frequency > 0:
                try:
                    self.postImage()
                except:
                    traceback.print_exc()

            time_since_update = time.perf_counter() - last_update
            if time_since_update > self.update_frequency:
                minutes_elapsed = str(int(time_since_update // 60))
                seconds_elapsed = str(int(time_since_update % 60))
                if len(seconds_elapsed) == 1:
                    seconds_elapsed = "0" + seconds_elapsed
                time_str = minutes_elapsed + ":" + seconds_elapsed
                print("VISITED DICT: " + str(self.visited))
                comments_made = len([i for i in self.visited if self.visited[i] == 1])
                self.printInfo(["Routine Update:", "Comments made over the last {} minutes: {}".format(time_str, comments_made)])
                last_update = time.perf_counter()
                self.visited = dict()
                self.updateQuarantinedUsers()
                self.checkBotHealth()
