FROM python:3.12

# Set environment variables
ENV PIP_DISABLE_PIP_VERSION_CHECK 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /src

# Install dependencies
COPY services/backend/src/requirements.txt .
RUN pip install -r requirements.txt

# Copy project
COPY . .

# Just keep running.
ENTRYPOINT ["tail", "-f", "/dev/null"]