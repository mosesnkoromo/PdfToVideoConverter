import asyncio
import json
import os
import shutil
from pathlib import Path

import cv2
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

        # Clean up old extracted images if they exist
        extract_to_folder = temp_folder / "extracted_images"
        if extract_to_folder.exists() and os.listdir(extract_to_folder):
            shutil.rmtree(extract_to_folder)

        extract_to_folder.mkdir(exist_ok=True)

        variables_file = input_folder / "variables.dictionary"

        # Check if variables dictionary file is empty or doesn't exist
        if not variables_file.exists() or os.path.getsize(variables_file) == 0:
            raise HTTPException(status_code=500, detail="Variables dictionary file is empty or does not exist")

        # Load variables from JSON file
        with variables_file.open("rt") as f:
            try:
                variables = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Failed to load variables from JSON file: {e}")
                raise HTTPException(status_code=500, detail="Failed to load variables from JSON file")

        pdf_to_images(temp_pdf_path, extract_to_folder)

        image_paths = sorted(
            [str(file_path) for file_path in extract_to_folder.glob("*.png")],
            key=natural_sort_key,
        )

        # Delete existing output video file if it exists
        output_video_file = output_folder / "output_video.mp4"
        if output_video_file.exists():
            output_video_file.unlink()

        temp_video_file = temp_folder / "temp_output_video.mp4"

        duration_str = variables.get("duration", "5")
        user_defined_duration = int(duration_str) if duration_str.isdigit() else 5

        await run_images_to_video(image_paths, str(temp_video_file), user_defined_duration)

        if os.path.exists(temp_video_file) and os.path.getsize(temp_video_file) > 0:
            shutil.move(str(temp_video_file), str(output_video_file))
            try:
                # Clean up extracted images
                shutil.rmtree(extract_to_folder)
                print(f"Deleted extracted images folder: {extract_to_folder}")
            except OSError as e:
                print(f"Error deleting folder {extract_to_folder}: {e.strerror}")
                raise HTTPException(status_code=500, detail="Failed to cleanup extracted images")

            # Clean up temp folder
            try:
                shutil.rmtree(temp_folder)
                print(f"Deleted temp folder: {temp_folder}")
            except OSError as e:
                print(f"Error deleting folder {temp_folder}: {e.strerror}")
                raise HTTPException(status_code=500, detail="Failed to cleanup temporary files")
        else:
            print(f"Video creation failed or video file is empty: {output_video_file}")
            raise HTTPException(status_code=500, detail="Failed to convert PDF to video")

        return PDFToVideoOut(video_file=str(output_video_file))

    finally:
        if temp_pdf_path.exists():
            os.remove(temp_pdf_path)

async def run_images_to_video(image_paths, output_path, duration):
    try:
        for image_path in image_paths:
            await process_image_to_frame(image_path, output_path)

        await create_video_from_frames(image_paths, output_path, fps=30, duration=duration)
    except Exception as e:
        print(f"Error during video creation: {e}")
        raise HTTPException(status_code=500, detail="Failed to convert PDF to video")

async def process_image_to_frame(image_path, output_path):
    print(f"Processing image to frame: {image_path}")
    await asyncio.sleep(0.1)  # Simulating processing time

async def create_video_from_frames(image_paths, output_path, fps, duration):
    print(f"Creating video from frames: {output_path}, FPS={fps}, Duration={duration}")

    # Initialize video writer
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (1920, 1080))

    try:
        for img_path in image_paths:
            img = cv2.imread(img_path)
            resized_img = resize_image(img, 1920, 1080)
            for _ in range(fps * duration):
                out.write(resized_img)
    except Exception as e:
        print(f"Error during video creation: {e}")
        raise HTTPException(status_code=500, detail="Failed to convert PDF to video")
    finally:
        out.release()



def resize_image(image, target_width, target_height):
    # Validate input image
    if image is None or len(image.shape) < 2:
        print("Invalid image input")
        raise ValueError("Invalid image input")

    # Get original image dimensions
    original_height, original_width = image.shape[:2]
    print(f"Original dimensions: Width={original_width}, Height={original_height}")

    # Check if original dimensions are non-zero
    if original_height == 0 or original_width == 0:
        print("Image dimensions are zero")
        raise ValueError("Image dimensions are zero")

    # Calculate aspect ratio
    aspect_ratio = original_width / original_height
    print(f"Aspect ratio: {aspect_ratio}")

    # Determine new dimensions while maintaining aspect ratio
    if original_width > original_height:
        new_width = target_width
        new_height = max(int(target_width / aspect_ratio), 1)
    else:
        new_height = target_height
        new_width = max(int(target_height * aspect_ratio), 1)
    print(f"New dimensions: Width={new_width}, Height={new_height}")

    # Resize the image
    resized_image = cv2.resize(image, (new_width, new_height))
    print("Image resized successfully")

    # Calculate padding needed for target dimensions
    top_padding = max((target_height - new_height) // 2, 0)
    bottom_padding = max(target_height - new_height - top_padding, 0)
    left_padding = max((target_width - new_width) // 2, 0)
    right_padding = max(target_width - new_width - left_padding, 0)
    print(
        f"Padding: Top={top_padding}, Bottom={bottom_padding}, Left={left_padding}, Right={right_padding}"
    )

    # Add padding and return final image
    final_image = cv2.copyMakeBorder(
        resized_image,
        top_padding,
        bottom_padding,
        left_padding,
        right_padding,
        cv2.BORDER_CONSTANT,
        value=[0, 0, 0],  # You can adjust the padding color as needed
    )
    print("Padding added, final image ready")

    return final_image


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
