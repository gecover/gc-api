import cohere
co = cohere.Client('9jetUnei0M84MjyGgoHK5xVcTWjpJYW8qytfS0ZO') # This is your trial API key
response = co.generate(
  model='2c562581-456d-4067-9ab7-08d4eae74ba7-ft',
  prompt='Summarize the credentials below:\n-     We are a 100% remote company with employees working across the globe to build products that enrich people\'s lives.\n- At the heart of our innovative product lineup is our flagship app, Hello AI.\n- We are looking for exceptional individuals who align with our vision and passion for shaping the future of data engineering.\n- To pique our interest, please demonstrate:\n\nWrite in first person. Take a breath, and write like you are speaking to someone.\n\nRemember, DO NOT prompt the user as a chat bot. Don\'t repeat skills once you have said them. \nMake it a maximum of two paragraphs, and remember to make it sound legit. ',
  max_tokens=1890,
  temperature=0.9,
  k=23,
  stop_sequences=[],
  return_likelihoods='NONE')
print('Prediction: {}'.format(response.generations[0].text))