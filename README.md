# xud-docker-bot 🤖

This bot integrates DockerHub, GitHub, Travis CI and Discord together to provide timely and helpful feedback for [xud-docker](https://github.com/exchangeunion/xud-docker).


### HTTP Endpoints

* `/`: The index page;
* `/webhooks/dockerhub`: The DockerHub webhook notifying new image tags pushed;
* `/webhooks/github`: The GitHub webhook notifying new commits pushed to repositories;
* `/webhooks/travis`: The Travis webhook notifying job state updates;
* `/health`: Show Discord client state.


### Discord commands

* `!help`: Show help information about available commands;
* `!build [-b <branch>] [-p <platform>] <image> [<image>...]`: Build images;
* `!ping`: Ping the bot.