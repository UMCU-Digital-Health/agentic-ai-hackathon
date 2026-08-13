
# Agentic AI Hackathon
**TeamAI** - August 2026

----

Welcome to the Agentic AI Hackathon!

## MLFlow
We use a shared MLFlow server. It runs from `../agentic_hackathon_aug_2026/mlflow_server/`. The only thing you have to do is a port-forward and make sure to log runs to your experiment.

### Port-forward

- In VS Code, go to the `PORTS` section, next to your terminal. Or press `command+shift+p` and select: `Ports: Focus on Ports View`
- Click on `Add Port` and forward to `5068`. 
- Now you should be able to reach the MLFlow server on http://localhost:5068/


### Logging your runs
In your notebook or script, before any logging calls:

```python
import mlflow

mlflow.set_tracking_uri("http://localhost:5068")
mlflow.set_experiment("your-team-name")
```

### When the MLFLow server is down (optional)
We'll make sure the server is running. Should you want to use the server after the hackathon, from the `../agentic_hackathon_aug_2026/mlflow_server/` run:

```bash
uv sync
uv run mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlartifacts --port 5068
```