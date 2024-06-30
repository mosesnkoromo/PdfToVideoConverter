import asyncio
import json
import os
import shutil
from pathlib import Path

from dotenv import dotenv_values
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from image_processing import natural_sort_key
from pdf_processing import pdf_to_images

class PDFToVideoOut(BaseModel):
    video_file: str

CONF = dotenv_values(".env")

app = FastAPI(description="Slideshow-to-Video Converter")
app.mount("/files", StaticFiles(directory="files"), "files")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", status_code=200)
def root():
    return {"message": "Hello World"}

@app.post("/convert", response_model=PDFToVideoOut)
async def convert(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        temp_pdf_path = Path("files") / file.filename
        with open(temp_pdf_path, "wb") as pdf_file:
            pdf_file.write(contents)

        input_folder = Path(os.getenv("CROSSCOMPUTE_INPUT_FOLDER", "batches/standard/input"))
        output_folder = Path("files")
        output_folder.mkdir(parents=True, exist_ok=True)

        temp_folder = output_folder / "temp"
        temp_folder.mkdir(exist_ok=True)
        temp_video_file = temp_folder / "temp_output_video.mp4"

        extract_to_folder = temp_folder / "extracted_images"
        extract_to_folder.mkdir(exist_ok=True)

        with (input_folder / "variables.dictionary").open("rt") as f:
            variables = json.load(f)

        pdf_to_images(temp_pdf_path, extract_to_folder)

        image_paths = sorted(
            [str(file_path) for file_path in extract_to_folder.glob("*.png")],
            key=natural_sort_key,
        )

        output_video_file = output_folder / "output_video.mp4"

        duration_str = variables.get("duration", "5")
        user_defined_duration = int(duration_str) if isinstance(duration_str, str) and duration_str.isdigit() else 5

        await run_images_to_video(image_paths, str(temp_video_file), user_defined_duration)

        if os.path.exists(temp_video_file) and os.path.getsize(temp_video_file) > 0:
            shutil.move(str(temp_video_file), str(output_video_file))
            try:
                shutil.rmtree(temp_folder)
            except OSError as e:
                print(f"Error deleting folder {temp_folder}: {e.strerror}")
                raise HTTPException(status_code=500, detail="Failed to cleanup temporary files")
        # else:
        #     print(f"Video creation failed or video file is empty: {output_video_file}")
        #     raise HTTPException(status_code=500, detail="Failed to convert PDF to video")

        return PDFToVideoOut(video_file=str(output_video_file))

    finally:
        if temp_pdf_path.exists():
            os.remove(temp_pdf_path)

async def run_images_to_video(image_paths, output_path, duration):
    try:
        for image_path in image_paths:
            await process_image_to_frame(image_path, output_path)

        await create_video_from_frames(output_path, fps=30, duration=duration)
    except Exception as e:
        print(f"Error during video creation: {e}")
        raise HTTPException(status_code=500, detail="Failed to convert PDF to video")

async def process_image_to_frame(image_path, output_path):
    print(f"Processing image to frame: {image_path}")
    await asyncio.sleep(0.1)  # Simulating processing time

async def create_video_from_frames(output_path, fps, duration):
    print(f"Creating video from frames: {output_path}, FPS={fps}, Duration={duration}")
    await asyncio.sleep(1)  # Simulating video creation time
    print("Video creation completed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
