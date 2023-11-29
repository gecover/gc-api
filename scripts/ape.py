from openai import OpenAI

posting = """

Technical Requirements

You have at least a bachelor’s degree in computer science, mathematics, software engineering, business analytics, or a related discipline. 
You have expert-level Python skills.
You have professional software development experience related to AI, ML, or data science with strong knowledge of related frameworks (e.g. transformers, PyTorch, scikit-learn, Pandas).
You have experience integrating machine learning projects from Jupyter Notebooks into engineering systems and cloud environments
You have experience working with cloud service providers and APIs
You are highly literate in the AI research space. You regularly read research papers and other technical publications as part of your work.
You are excited about building frameworks and applications on top of foundation models including proprietary models like GPT-4 and more open models like Llama 2.
You have experience with prompt engineering and doing Retrieval Augmented Generation with LLM’s using vector databases. 
You are passionate about the measurable impact of your work, and you are equally excited about publishing code and supporting material.
You have experience training or fine-tuning machine learning models.
You have experience creating demos of applied research.

Other Skills& Attributes

You have experience or a strong desire to engage directly with clients, understanding their unique needs, and presenting tailored AI solutions. Your business acumen helps you recognize market trends, client challenges, and opportunities for ChainML to make an impact.
Strong communication skills, especially in written English for creating educational content, as well as public speaking and participating in panels.
Passion for engaging with communities and users across various platforms.
Flexibility and adaptability in a fast-paced startup environment.
Comfortable working primarily from home and collaborating remotely.
Proactive in seeking feedback or brainstorming with team members.
A positive and creative approach, always open to sharing and implementing new ideas.
Ability to manage a busy schedule, especially during events or conferences.
Ability to create and update useful documentation, as well as use a CRM system

Core Responsibilities

Design, develop, and refine content and tools to support client engagements and the integration of Council into client systems
Collaborate with various teams such as research, engineering, and sales to understand client needs, craft effective solution content, and deliver engaging training experiences.
Build and nurture relationships with key industry figures and the wider community, positioning ChainML as a trusted name in AI integration.
Keep a close eye on feedback and data, constantly improving our client offerings based on user needs and industry trends.
Represent ChainML at industry events, promoting our educational resources and forming connections with potential partners and clients.
Showcase the capabilities of our Council platform through demos, hands-on sessions, and other interactive events.
"""

prompt = f"Please extract the most important job requirements from the following job posting and list them in point form: {posting}."
from dotenv import load_dotenv, find_dotenv

env_file = find_dotenv(".env.dev")
load_dotenv(env_file)

client = OpenAI()

completion = client.chat.completions.create(
  model="gpt-3.5-turbo",
  messages=[
    {"role": "user", "content": prompt},
  ]
)

print(completion.choices[0].message.content)

output = """- Bachelor's degree in computer science, mathematics, software engineering, business analytics, or related discipline
- Expert-level Python skills
- Professional software development experience in AI, ML, or data science
- Strong knowledge of frameworks like transformers, PyTorch, scikit-learn, Pandas
- Experience integrating machine learning projects into engineering systems and cloud environments
- Familiarity with cloud service providers and APIs
- Literacy in AI research, regularly reading research papers and technical publications
- Experience working with foundation models like GPT-4 and Llama 2
- Experience in prompt engineering and Retrieval Augmented Generation using vector databases
- Experience in training or fine-tuning machine learning models
- Experience in creating demos of applied research
- Experience or strong desire to engage directly with clients and present tailored AI solutions
- Strong communication skills in written English, public speaking, and participating in panels
- Passion for engaging with communities and users on various platforms
- Flexibility and adaptability in a fast-paced startup environment
- Comfortable working remotely from home
- Proactive in seeking feedback and brainstorming with team members
- Positive and creative approach, open to sharing and implementing new ideas
- Ability to manage a busy schedule, especially during events or conferences
- Ability to create and update useful documentation and use CRM system
- Designing, developing, and refining content and tools for client engagements and integration of Council into client systems
- Collaborating with research, engineering, and sales teams to understand client needs and deliver effective solutions
- Building relationships with industry figures and the wider community to position ChainML as a trusted name in AI integration
- Constantly improving client offerings based on feedback and industry trends
- Representing ChainML at industry events and promoting educational resources
- Showcasing the capabilities of Council platform through demos and interactive events."""

