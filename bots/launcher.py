import subprocess
import os

def launch():
    subprocess.run(["docker", "compose", "-f", "docker/docker-compose.yml", "up", "-d"])

if __name__ == "__main__":
    launch()