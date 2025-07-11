# CS 152 - Trust and Safety Engineering

## Repository Details:

This repository holds the code for CS152 Group 12's project on doxxing. The context of this platform is a feed-based platform, similar to X (formerly Twitter) and Facebook. The bot was coded using discord.py and created by CS152's Group 12 (Sara Bukair, Ismael Duran, Dilnaz Kamalova, Alison Rogers, Esha Thapa) at Stanford University, Spring 2025.

## Guide to Key Files:

- `bot.py` lays out the code to initialize the discord bot, process a message, and return automated responses
- `report.py` contains the code relevant to users trying to make a report. It follows our user report flow and sends the report to the moderator channel.
- `review.py` contains the code relevant to users trying to review a report.
  - To keep the moderator channel streamlined, it is only accessible via DM.
  - To keep the reviewing process secure, you must enter a password in the DMs with the bot. For testing purposes, the password is currently `modpassword`. This can (and should) be changed for live production.
- `claude_detector.py` contains the code for querying Claude 3.5 Haiku for our automated detection system, as well as formatting the response from the API.
- `supabase_helper.py` contains the code for entering and querying our databse for victim and offender statistics

There are various other files in this codebase that were used for testing purposes. These include `gemini_detector.py`, `run_claude_test.py`, `run_gemini_test.py`, and others.

## Tour of the System:

### Main Channel

The main channel is where users send and read messages sent on our platform. It includes the users, moderators, and bot.

### Moderator Channel

The moderator channel is where reports and reviews are sent to the moderator team, whether manual or automated. To reduce channel spam, no decision-making is directly broadcasted into this channel.

### Bot DMs

DMing the bot is how human users can create reports (kept out of the main channel to maintain anonymity) and how human moderators can review reports and review AI decision-making logic (kept out of the moderator channel to keep the moderator channel streamlined and relevant to all moderators).

Users will also receive updates via DM about the result of their reports, as well as any reports taken against them that result in action taken against their own message/account. To reduce reporting misuse, reviews that result in no action against a post/account are not sent to the account that was reported. Users will also receive updates on whether their action is at risk of being suspended/banned (warning), being suspended, or being banned.

## User Capabilities

### Non-Moderator User Capabilities

Users may send messages in the main guild channel, edit their own messages, report messages via DMing the bot, and ask the bot to see the platform-wide policy on doxxing. Users may report a message for a variety of abuses, though only the doxxing flow is thoroughly built out.

### Moderator Capabilities

Moderators in this channel may view and send messages in the main channel. They may also view and send messages in the moderator channel, which will include any incoming reports and the results of any reviews (including instances where the automated detection mechanism detects an example of doxxing).

Moderators interact with the bot via DM to keep the moderator channel from being bogged down by the decisions of every moderator on every report. in these DMs, moderators may:

- Ask the bot for further information any AI evaluation of a post as either possibly or definitely doxxing
- Ask to see the user-facing doxxing policy
- Ask for a report to review
  - The moderator bot will send over if one is in the queue, the moderator does not need to search for a report in the moderator channel.
  - These reports will be sent to moderators automatically prioritized by recency, risk to victim, risk of information, and other metrics.

Moderators may report a message for a variety of abuses, though only the doxxing flow is thoroughly built out.

### Bot Capabilities

The bot automatically evaluates every message sent in the chat. If it has a high confidence it is doxxing, it will delete the post and update the moderator channel with its decision. If it has a medium confidence the post is doxxing, it will create a report, add it to the report queue, and send a notice in the moderator channel about the new report. When the bot sends a notice in the channel from the evaluation system, it stores further details and reasoning in a dictionary for moderator evaluation (via DM only) if desired.

The bot interacts with users and moderators via DM to create reports, review reports, and update users based on reports.

The bot sends any manual report made to the moderator channel in chronological order and puts them into a priority queue for moderator review. It also sends the result of any review completed by moderators into the moderator channel.

The bot is able to delete messages from the chat, message users about any action taking on their reports, and message users about any action taken against their post or account. Suspension and banning of accounts is only simulated for now.

## To Run Locally:

To run the code, you will need to join the CS152 Discord and join your group's channel. You will then need to create your own tokens.json file including API keys for "discord" and "anthropic".

If you would like to run any of the code involving Gemini, you will need to add "project_id" to your tokens.json file, as well as create a google-credentials.json file with your own Google Gemini credentials.

## Testing Results:

We tested our bot on two different LLMs: Gemini and Claude 3.5 Haiku. The results from these tests (`run_claude_test.py` and `run_gemini_test.py`) can be found at [this Google Drive link](https://docs.google.com/spreadsheets/d/1KHp2se-1uidbA1BWqDK5u3bXwcOJtIicQbQcH-HyHj0/edit?usp=drive_link). Here, you will see our accuracy, precision, recall, and F1 scores for both models (based on different confidence thresholds), as well as some further insights into the tradeoffs of each model. This includes the distribution of confidence levels across models, considerations as to how each model would affect the moderator workload, and how each model would affect user experience.

## Demo Video:

You may find a demo video of our bot's functionality at [this Google Drive link](https://drive.google.com/file/d/1GqUQ0GqNsCQb8rSyFxAVnt7wuZ4r1Mg2/view?usp=sharing).

## AI Citation:

In this project, AI was used to:

- Add comments to initial draft of `run_gemini_test.py` (which has since been completely rewritten without using AI)
- Debug issues connecting initial draft of `run_gemini_test.py`
- Generate testing based on handwritten examples and edge cases, as there are are no publicly available datasets on doxxing available. Some generated posts were also used in prompt engineering.
- Debugging Gemini API connectivity and `check_connection.py`
