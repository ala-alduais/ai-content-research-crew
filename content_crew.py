"""
AI Content Research Crew

A sequential multi-agent pipeline that researches a topic on the web,
fact-checks what it found, turns it into a content brief, writes a
Twitter/X thread and an Instagram caption, and has an editor polish both.
"""

import os
from typing import List

from dotenv import load_dotenv
from pydantic import BaseModel
from crewai import LLM, Agent, Crew, Process, Task
from crewai_tools import SerperDevTool

load_dotenv()  # reads GOOGLE_API_KEY and SERPER_API_KEY from .env

llm = LLM(
    model=os.getenv("MODEL", "gemini/gemini-3.6-flash"),
    temperature=0.3,
)

search_tool = SerperDevTool()


# ---------------------------------------------------------------- Agents
researcher = Agent(
    role="Trend Researcher",
    goal="Find the most current, accurate, and engaging angles and facts on the given topic.",
    backstory="You are an expert digital researcher who finds strong narratives and compelling statistics.",
    tools=[search_tool],
    allow_delegation=False,
    verbose=True,
    llm=llm,
)

strategist = Agent(
    role="Content Strategist",
    goal="Distill research into a unified content brief with key messaging pillars.",
    backstory="You turn raw findings into clear campaign briefs so all platforms share the same core message.",
    allow_delegation=False,
    verbose=True,
    llm=llm,
)

twitter_writer = Agent(
    role="Twitter/X Writer",
    goal="Write a punchy, engaging 5-7 tweet thread with strong hooks.",
    backstory="You are a master of concise writing that stops the scroll and drives retweets.",
    allow_delegation=False,
    verbose=True,
    llm=llm,
)

instagram_writer = Agent(
    role="Instagram Writer",
    goal="Write a visual-first caption with relevant hashtags and calls to action.",
    backstory="You understand aesthetic spacing, emoji usage, and engaging social copywriting.",
    allow_delegation=False,
    verbose=True,
    llm=llm,
)

editor = Agent(
    role="Brand Editor",
    goal="Review and materially improve both outputs for brand consistency, voice, and quality.",
    backstory=(
        "You are a demanding editor who never rubber-stamps a first draft. "
        "You actively rewrite weak phrasing, tighten copy, and flag anything "
        "factually shaky. Simply repeating a draft back unchanged is a failure."
    ),
    allow_delegation=False,
    verbose=True,
    llm=llm,
)


# ------------------------------------------------------- Structured output
class TweetThread(BaseModel):
    tweets: List[str]    # each item is one standalone, postable tweet
    hashtags: List[str]  # 2-3 hashtags shared across the thread


# ----------------------------------------------------------------- Tasks
research_task = Task(
    description="Search the internet and find 3-4 key trends, statistics, or facts about: {topic}.",
    expected_output="A bulleted list of 3-4 findings and statistics, each with its source.",
    agent=researcher,
)

fact_check_task = Task(
    description=(
        "Review the findings you just gathered. For each one, check whether the year, "
        "percentage, or statistic still makes sense as a CURRENT fact given today's date. "
        "Flag or correct anything that reads like a stale or outdated projection. "
        "Re-search if a finding looks outdated or you're unsure about its accuracy. "
        "Return only findings you are confident are current and accurate."
    ),
    expected_output=(
        "A verified bulleted list of 3-4 current, accurate findings, each with its source "
        "and a note confirming it was checked for recency."
    ),
    context=[research_task],
    agent=researcher,
)

strategy_task = Task(
    description=(
        "Using the verified research findings, create a brief outlining the core message, "
        "target audience, and main angle."
    ),
    expected_output="A concise content brief with core messaging and campaign angle.",
    context=[fact_check_task],
    agent=strategist,
)

twitter_task = Task(
    description=(
        "Using the content brief, write an engaging Twitter/X thread of 5-7 tweets. "
        "Each tweet must be a SEPARATE, standalone item under 280 characters. "
        "Structure it as a hook, 3-5 body tweets, and a closing call-to-action tweet. "
        "Include 2-3 relevant hashtags."
    ),
    expected_output="A tweet thread with each tweet as a separate list item, plus a shared hashtag list.",
    context=[strategy_task],
    agent=twitter_writer,
    output_pydantic=TweetThread,
)

instagram_task = Task(
    description=(
        "Using the content brief, write an Instagram caption. Suggest a visual or reel "
        "concept, write formatted body text with emojis, and list 5-8 relevant hashtags."
    ),
    expected_output="A ready-to-publish Instagram caption in Markdown with a visual concept and hashtags.",
    context=[strategy_task],
    agent=instagram_writer,
)

edit_task = Task(
    description=(
        "Review the Twitter/X thread and the Instagram caption. You must make at least one "
        "concrete improvement to each: tighten weak phrasing, remove anything that is not "
        "real post content, and keep both aligned with the same core message. "
        "List the specific edits you made."
    ),
    expected_output=(
        "A final content report with the edited Twitter/X thread, the edited Instagram "
        "caption, and a list of the specific edits made."
    ),
    context=[twitter_task, instagram_task],
    agent=editor,
)


# ------------------------------------------------------------------ Crew
content_crew = Crew(
    agents=[researcher, strategist, twitter_writer, instagram_writer, editor],
    tasks=[research_task, fact_check_task, strategy_task, twitter_task, instagram_task, edit_task],
    process=Process.sequential,
    verbose=True,
)


if __name__ == "__main__":
    topic = os.getenv("TOPIC", "The rise of AI agents in enterprise automation")
    print(f"Starting Content Research Crew for topic: {topic}\n")
    result = content_crew.kickoff(inputs={"topic": topic})

    os.makedirs("output", exist_ok=True)
    with open("output/final_content.md", "w", encoding="utf-8") as f:
        f.write(str(result))

    print("\n" + "=" * 50)
    print("FINAL CONTENT (also saved to output/final_content.md)")
    print("=" * 50 + "\n")
    print(result)
