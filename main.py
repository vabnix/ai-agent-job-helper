from datetime import datetime
import os

import yaml
import pandas as pd
from crewai import Agent, Task, Crew
from typing import List
from pydantic import BaseModel, Field
import re
# Define file paths for YAML configurations
files = {
    'agents': 'config/agents.yaml',
    'tasks': 'config/tasks.yaml'
}

# Load configurations from YAML files
configs = {}
for config_type, file_path in files.items():
    with open(file_path, 'r') as file:
        configs[config_type] = yaml.safe_load(file)

# Assign loaded configurations to specific variables
agents_config = configs['agents']
tasks_config = configs['tasks']


# Create Pydantic Models for Structured Output
class TaskEstimate(BaseModel):
    task_name: str = Field(..., description="Name of the task")
    estimated_time_hours: float = Field(..., description="Estimated time to complete the task in hours")
    required_resources: List[str] = Field(..., description="List of resources required to complete the task")


class Milestone(BaseModel):
    milestone_name: str = Field(..., description="Name of the milestone")
    tasks: List[str] = Field(..., description="List of task IDs associated with this milestone")


class ProjectPlan(BaseModel):
    tasks: List[TaskEstimate] = Field(..., description="List of tasks with their estimates")
    milestones: List[Milestone] = Field(..., description="List of project milestones")


# Create Agents
project_planning_agent = Agent(
    config=agents_config['project_planning_agent']
)

estimation_agent = Agent(
    config=agents_config['estimation_agent']
)

resource_allocation_agent = Agent(
    config=agents_config['resource_allocation_agent']
)

# Create Tasks
task_breakdown = Task(
    config=tasks_config['task_breakdown'],
    agent=project_planning_agent
)

time_resource_estimation = Task(
    config=tasks_config['time_resource_estimation'],
    agent=estimation_agent
)

resource_allocation = Task(
    config=tasks_config['resource_allocation'],
    agent=resource_allocation_agent,
    output_pydantic=ProjectPlan
)

# Create Crew
crew = Crew(
    agents=[
        project_planning_agent,
        estimation_agent,
        resource_allocation_agent
    ],
    tasks=[
        task_breakdown,
        time_resource_estimation,
        resource_allocation
    ],
    verbose=True
)


def extract_gantt_chart(text: str) -> str:
    """Extract Gantt chart from the conversation text"""
    gantt_pattern = r'### Gantt Chart\n\|.*?\n\|.*?\n((?:\|.*?\n)*)'
    match = re.search(gantt_pattern, text, re.DOTALL)
    if match:
        return "### Gantt Chart\n|" + match.group(1)
    return ""


def save_metrics(metrics_dir: str, crew_output: str, costs: float) -> None:
    """Save all metrics including Gantt chart to files"""
    # Create output directory
    os.makedirs(metrics_dir, exist_ok=True)

    # Save costs
    with open(f"{metrics_dir}/cost.txt", 'a+') as cost_file:
        cost_file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Total costs: ${costs:.4f}\n")

    # Extract and save Gantt chart if present
    gantt_chart = extract_gantt_chart(crew_output)
    if gantt_chart:
        with open(f"{metrics_dir}/gantt_chart.md", 'a+') as gantt_file:
            gantt_file.write(f"\n\n# Gantt Chart - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            gantt_file.write(gantt_chart)

    # Save full conversation
    with open(f"{metrics_dir}/full_output.txt", 'a+') as output_file:
        output_file.write(f"\n\n=== New Run - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        output_file.write(crew_output)

def main():
    # Project inputs
    project = 'Website'
    industry = 'Technology'
    project_objectives = 'Create a website for a small business'
    team_members = """
    - John Doe (Project Manager)
    - Vaibhav Srivastava (Development Lead)
    - Bob Smith (Designer)
    - Alice Johnson (QA Engineer)
    - Tom Brown (QA Engineer)
    """
    project_requirements = """
    - Create a responsive design that works well on desktop and mobile devices
    - Implement a modern, visually appealing user interface with a clean look
    - Develop a user-friendly navigation system with intuitive menu structure
    - Include an "About Us" page highlighting the company's history and values
    - Design a "Services" page showcasing the business's offerings with descriptions
    - Create a "Contact Us" page with a form and integrated map for communication
    - Implement a blog section for sharing industry news and company updates
    - Ensure fast loading times and optimize for search engines (SEO)
    - Integrate social media links and sharing capabilities
    - Include a testimonials section to showcase customer feedback and build trust
    """

    # Execute crew tasks
    result = crew.kickoff()

    # Display metrics
    costs = 0.150 * (crew.usage_metrics.prompt_tokens + crew.usage_metrics.completion_tokens) / 1_000_000
    print(f"Total costs: ${costs:.4f}")

    # Save all metrics including Gantt chart
    save_metrics("outputs/metrics", str(result), costs)

    # Create output directory if it doesn't exist
    os.makedirs("outputs/metrics", exist_ok=True)

    with open("outputs/metrics/cost.txt", 'a+') as cost_file:
        cost_file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Total costs: ${costs:.4f}")

    # Convert UsageMetrics to DataFrame
    df_usage_metrics = pd.DataFrame([crew.usage_metrics.dict()])
    print("\nUsage Metrics:")
    print(df_usage_metrics)
    with open("outputs/metrics/cost.txt", 'a+') as usage_metric_file:
        usage_metric_file.write(f"\nUsage Metrics: \n{df_usage_metrics}")

    # Display tasks and milestones
    tasks = result.pydantic.dict()['tasks']
    df_tasks = pd.DataFrame(tasks)
    print("\nTask Details:")
    with open("outputs/metrics/task_details.txt", 'w+') as task_file:
        task_file.write(f"\nTask Details: \n{df_tasks}")
    print(df_tasks)

    milestones = result.pydantic.dict()['milestones']
    df_milestones = pd.DataFrame(milestones)
    print("\nMilestone Details:")
    with open("outputs/metrics/milestone_details.txt", 'w+') as milestone_details_file:
        milestone_details_file.write(f"\nMilestone Details: \n{df_milestones}")
    print(df_milestones)

    # Display Gantt chart if present
    gantt_chart = extract_gantt_chart(str(result))
    if gantt_chart:
        print("\nGantt Chart:")
        print(gantt_chart)


if __name__ == "__main__":
    main()