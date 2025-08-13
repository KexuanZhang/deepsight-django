"""Panel crew collaboration module for dynamic expert discussions."""

import logging
import os
from pathlib import Path

from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource
from .tools import SafeSearchTool


# Store in project directory
project_root = Path(__file__).parent
storage_dir = project_root / "crewai_storage"

os.environ["CREWAI_STORAGE_DIR"] = str(storage_dir)

# Configure logging
logger = logging.getLogger(__name__)

manager_llm = LLM(model="openai/gpt-4.1", temperature=0.1)
engineer_llm = LLM(model="openai/gpt-4.1", temperature=0.5)
research_llm = LLM(model="anthropic/claude-3-5-sonnet-20241022", temperature=0.5)
content_llm = LLM(model='gemini/gemini-2.5-pro', temperature=0.1)


@CrewBase
class PanelCrewCollaboration:
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    
    def __init__(self, material_content: str = "") -> None:
        super().__init__()
        # Tools
        self.search_tool = SafeSearchTool()

        # Create knowledge source from material content if provided
        if material_content:
            self.material_knowledge_source = StringKnowledgeSource(
                content=f"Discussion Material Content:\n\n{material_content}"
            )
        else:
            self.material_knowledge_source = ""

    # Panel discussion agents
    @agent
    def moderator(self) -> Agent:
        return Agent(
            config=self.agents_config['moderator'],
            tools=[self.search_tool],
            llm=manager_llm
        )

    @agent
    def ai_scientist(self) -> Agent:
        return Agent(
            config=self.agents_config['ai_scientist'],
            tools=[self.search_tool],
            llm=engineer_llm
        )

    @agent
    def ai_researcher(self) -> Agent:
        return Agent(
            config=self.agents_config['ai_researcher'],
            tools=[self.search_tool],
            llm=engineer_llm
        )

    @agent
    def cs_professor(self) -> Agent:
        return Agent(
            config=self.agents_config['cs_professor'],
            tools=[self.search_tool],
            llm=research_llm
        )
    
    @agent
    def conversation_optimizer(self) -> Agent:
        return Agent(
            config=self.agents_config['conversation_optimizer'],
            llm=content_llm
        )

    # Dynamic task - moderator analyzes input and selects appropriate experts
    @task
    def panel_discussion_task(self) -> Task:
        return Task(
            config=self.tasks_config['panel_discussion_task']
        )

    @task
    def polish_transcript_task(self) -> Task:
        return Task(
            config=self.tasks_config['polish_transcript_task'],
            context=[self.panel_discussion_task()]
        )

    @crew
    def crew(self) -> Crew:

        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )