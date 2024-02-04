from invoke import task
import subprocess
import docker


client = docker.from_env()

custom_docker_images = [
	"pbot-admin",
	"pbot-listener",
	"pbot-proxy",
	"pbot-bot"
]

@task
def devbounce(ctx):
	'''Deletes any old artifacts and rebuids & runs from scratch.'''
	# Prune non-running containers
	resp = client.containers.prune()

	# Delete pbot custom images
	current_images = client.images.list()
	for current_img in current_images:
		for image_name in custom_docker_images:
			if image_name in " ".join(current_img.tags):
				client.images.remove(image_name)

	subprocess.run(["docker-compose", "-ppbot", "-f./config/docker-compose.yml", "up"])