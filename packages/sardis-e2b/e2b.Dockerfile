FROM e2b/base:latest

# Install Python and Sardis SDK
RUN pip install sardis

# Set environment for simulation mode
ENV SARDIS_SIMULATION=true

# Pre-create a workspace directory
WORKDIR /home/user
