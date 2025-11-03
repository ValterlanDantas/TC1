from fastapi import APIRouter, BackgroundTasks
import subprocess, sys

router = APIRouter(prefix="/api/v1/scraping", tags=["insights"])

def _run_scraping_subprocess():
    # executa: python -m tc_01.scripts.scraping
    cmd = [sys.executable, "-m", "tc_01.scripts.scraping"]
    # se o script imprimir logs, eles aparecem no log do container
    subprocess.run(cmd, check=False)

@router.post("/trigger")
def trigger(background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_scraping_subprocess)
    return {"message": "scraping started"}
