from flask import Flask
from slackeventsapi import SlackEventAdapter
from slackclient import SlackClient
from urllib.parse import urlparse
from redminelib import Redmine
import pandoc
import os

application = app = Flask(__name__)

slack_signing_secret=os.environ["SLACK_SIGNING_SECRET"]
slack_events_adapter = SlackEventAdapter(slack_signing_secret, "/slack/events", app)

slack_bot_token=os.environ["SLACK_BOT_TOKEN"]
slack_client = SlackClient(slack_bot_token)

redmine_key=os.environ["REDMINE_API_KEY"]
redmine = Redmine('http://redmine.trypotdev.com', key=redmine_key)

def parse_url(url):
    parsed = urlparse(url)

    paths = parsed.path.split('/')

#    if parsed.netloc == "redmine.trypotdev.com" and paths[1] == "issues":
    if paths[1] == "issues":
        try:
            issue = redmine.issue.get(paths[2])
        except:
            print("Issue not found : " + paths[2])
            return { "title" : "TRYPOT Redmine", "text" : "존재하지 않는 이슈입니다" }

        user = redmine.user.get(issue.assigned_to.id)
        author = redmine.user.get(issue.author.id)

        doc = pandoc.Document()
        doc.html = issue.description.encode('utf-8')

        if "created_on" in dir(issue):
            create_date = " 이(가) " + issue.created_on.strftime("%Y/%m/%d") + "에 생성"
        else:
            create_date = ""

        if "due_date" in dir(issue):
            due_date = issue.due_date.strftime("%Y/%m/%d")
        else:
            due_date = "없음"

        content = {
                "title" : issue.project.name + " #" + paths[2] + " " + issue.subject,
                "title_link" : url,
                "color" : "#7cd197",
                "author_name" : issue.author.name + "(<@" + author.login + ">)" + create_date,
                "fields" : [
                    { "title" : "담당자",   "value" : issue.assigned_to.name + " <@" + user.login + ">", "short" : False },
                    { "title" : "상태",     "value" : issue.status.name, "short" : True },
                    { "title" : "우선순위", "value" : issue.priority.name, "short" : True },
                    { "title" : "시작시간", "value" : issue.start_date.strftime("%Y/%m/%d"), "short" : True},
                    { "title" : "완료기한", "value" : due_date, "short" : True }
                ],
                "text" : str(doc.markdown.decode('utf-8')),
                "footer" : "TRYPOT Studios Inc. floyd"
        }

        return content
    else:
        return ""

@slack_events_adapter.on("link_shared")
def handle_unfurl(event_data):
    message = event_data["event"]
    channel = message["channel"]
    message_ts = message["message_ts"]

    unfurls = {}

    for link in message["links"]:
        url = link["url"]
        unfurls[url] = parse_url(url)

    result = slack_client.api_call("chat.unfurl", ts=message_ts, channel=channel, unfurls=unfurls)
    if result["ok"] != True:
        print(result["error"])

@slack_events_adapter.on("error")
def error_handler(err):
    print("ERROR: " + str(err))

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=3001)
