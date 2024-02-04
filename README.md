# pbot3 | A Dockerized, GPT assisted, mean-spirited Discord bot. 

![](docs/assets/img/shodan_transparent.png)

What if SHODAN's pettyness and cruelty were directed at a hapless Discord server?

- Do your friends need to be put in their place?
- Have they grown soft and complacent within the confines of their confortable private servers?
- Release pbot in your Discord server and allow her to scortch ***and*** salt the earth!

-----

**Minimal effort approach:** throw a copy of pbot onto a spare Raspberry Pi in a tmux session and spew bad vibes into the noosphere passively. :sleeping::boom::broken_heart::hurtrealbad:
<br>

-----

# Usage

..

# Devlopment

Many development tasks are handled by the [invoke](https://docs.pyinvoke.org/en/stable/) python library. See `tasks.py`. 
Example: `invoke someTaskName`



## Work-In-Progress Stuff

### TODO:

- nix sqlite in favor of redis
- prompt(s) for 
  - openai?
  - bard?
  - madlib templates with AI supplied words?
- token tracking
- rate limiting
- Incite chaos!

### Links

- OpenAI [chatgpt](https://chat.openai.com/)
  - [API](https://platform.openai.com/docs/overview)
  - [OpenAI Cookbook](https://cookbook.openai.com/)
  - [Pricing](https://openai.com/pricing)
  - [Rate limits](https://platform.openai.com/docs/guides/rate-limits/?context=tier-free)
- https://stackoverflow.com/questions/48561981/activate-python-virtualenv-in-dockerfile
- https://pythonspeed.com/articles/activate-virtualenv-dockerfile/
- https://www.reddit.com/r/ChatGPT/comments/11gmcsi/openemotions_jailbreak_20_released/
- https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken
- Bard [chat](https://bard.google.com/chat)
    - https://aibard.online/bard-api-documentation/
    - https://github.com/ra83205/google-bard-api
- [Discord dev docs](https://discord.com/developers/applications)
- [Discord API](https://discordpy.readthedocs.io/en/stable/api.html#message)
- [discord.py](https://discordpy.readthedocs.io/en/stable/api.html)
- [best-practices-for-prompt-engineering-with-openai-api)](https://help.openai.com/en/articles/6654000-best-practices-for-prompt-engineering-with-openai-api)
- [https://platform.openai.com/docs/guides/prompt-engineering](https://platform.openai.com/docs/guides/prompt-engineering)
