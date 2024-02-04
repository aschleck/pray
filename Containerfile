FROM docker.io/python:3

RUN mkdir /app && useradd --create-home app
WORKDIR /app
COPY requirements.txt ./
COPY . .

USER app
RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python", "./runner.py" ]
