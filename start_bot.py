import praw
import time
import random

CLIENT_ID = None
CLIENT_SECRET = None
USER_AGENT = None
REDDIT_USERNAME = None
REDDIT_PASSWORD = None

reddit = praw.Reddit(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    user_agent=USER_AGENT,
    username = REDDIT_USERNAME,
    password=REDDIT_PASSWORD
)

def monitorPosts():
  visited = loadIDS()

  subreddit = reddit.subreddit(SUBREDDIT_NAME)
  start = time.perf_counter()
  print("Bot monitoring...")
  while time.perf_counter() - start < RUN_TIME:

      for submission in subreddit.new(limit = NO_SUBMISSIONS):
          submission.comments.replace_more(limit=None)

          dividor = "-------------------------------"
          post_title = submission.title
          for key_word in KEY_WORDS:
            if key_word in post_title.lower() and submission.id not in visited:

              try:
                print("=======================================================")
                print("TITLE: {}".format(post_title) + "\n" + dividor)
                addID(submission.id,visited)
                saveIDS(visited)

                response = returnResponse()
                submission.reply(response)
                print("RESPONSE: {}".format(response) + "\n" + dividor)
                print("=======================================================")
                time.sleep(WAIT_TIME)

              except praw.exceptions.APIException as e:
                print("API Exception, bot resuming in {} secs...".format(WAIT_TIME * 4))
                time.sleep(WAIT_TIME * 4)

          for top_comment in submission.comments:
            for key_word in KEY_WORDS:
              
              comment_txt = top_comment.body
              if key_word in comment_txt.lower() and top_comment.id not in visited and top_comment.author.name != reddit.user.me().name:
                try:
                  print("=======================================================")
                  print("COMMENT: {}".format(comment_txt) + "\n" + dividor)
                  addID(top_comment.id,visited)
                  saveIDS(visited)

                  response = returnResponse()
                  top_comment.reply(response)
                  print("RESPONSE: {}".format(response) + "\n" + dividor)
                  print("=======================================================")
                  time.sleep(WAIT_TIME)

                except praw.exceptions.APIException as e:
                  print("API Exception, bot resuming in {} secs...".format(WAIT_TIME * 4))
                  time.sleep(WAIT_TIME * 4)

  saveIDS(visited)
  time_elapsed = time.perf_counter() - start
  print("Bot ended. Time elapsed: {} secs".format(time_elapsed))

def addID(add_id,id_dict):
  add_id = str(add_id)
  if add_id in id_dict:
    return
  id_dict[add_id] = 0

def saveIDS(id_dict):
  with open("saved_ids.txt", mode ="w", encoding="utf-8") as write_file:
    for key in id_dict:
      write_file.write(str(key) + "\n")
    write_file.close()

def loadIDS():
  id_dict = dict()
  with open("saved_ids.txt", mode ="r", encoding="utf-8") as read_file:
    lines = read_file.readlines()
    for line in lines:
      line = line.rstrip()
      id_dict[line] = 0
    read_file.close()
  return id_dict


def getAllQuotes(filename):
  all_quotes = []
  with open(filename,mode="r",encoding="utf-8") as read_file:
    
    quotes = read_file.readlines()
    for quote in quotes:
      all_quotes.append(quote.rstrip())
    read_file.close()
  return all_quotes

def returnResponse():
  rand_index = random.randint(0,len(ALL_QUOTES)-1)
  rand_quote = ALL_QUOTES[rand_index]
  dividor = "=-=-=-=-=-=-=-=-=-=-=-=-=\n\n"
  response = 'Urahara Quote No.{}: \n\n{}"{}" - Kisuke Urahara'.format(rand_index+1,dividor,rand_quote)
  return response


FILENAME = "urahara_quotes.txt"
ALL_QUOTES = getAllQuotes(FILENAME)
RUN_TIME = 9999999999999999999999999999999999999999999999
SUBREDDIT_NAME = "bleach"
KEY_WORDS = ["urahara","kisuke"]
NO_SUBMISSIONS = 100
WAIT_TIME = 10


if __name__ == "__main__":
  monitorPosts()

