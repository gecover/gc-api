from datasets import load_dataset
import json
dataset = load_dataset("ShashiVish/cover-letter-dataset")

keys = ['Job Title', 'Preferred Qualifications', 'Hiring Company', 'Applicant Name', 'Past Working Experience', 'Current Working Experience', 'Skillsets', 'Qualifications', 'Cover Letter']
json_data = []

with open('scripts/output_file.jsonl', 'w') as jsonl_file:

    for x in range(len(dataset['train'])):
        qualification_input = dataset['train'][x]['Preferred Qualifications']
        pw_input = dataset['train'][x]['Past Working Experience']
        ce_input = dataset['train'][x]['Current Working Experience']
        skills_input = dataset['train'][x]['Skillsets']
        qual_input = dataset['train'][x]['Qualifications']

        prompt = f"""
        Summarize the credentials below:

        - {qualification_input}
        - {pw_input}
        - {ce_input}
        - {skills_input}
        - {qual_input}

        Write in first person. Take a breath, and write like you are speaking to someone.

        Remember, DO NOT prompt the user as a chat bot. Don't repeat skills once you have said them. 
        Make it a maximum of two paragraphs, and remember to make it sound legit. 
        """

        completion = (' ').join(dataset['train'][x]['Cover Letter'].split(',')[1:])

        jsonl_file.write(json.dumps({"prompt": prompt, "completition": completion}) + '\n')

    
