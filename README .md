
 ## PDF to Video Converter

PDF to Video Converter is a tool that transforms PDF documents into video files. This can be particularly useful for creating video presentations, tutorials, or any other application where you need to present PDF content in a video format.


## Acknowledgements

- This project uses ffmpeg for video processing
- PDF processing is handled by PyPDF2.
- Video frames are managed using opencv-python.
- Text-to-speech is provided by gTTS.

## API Reference

#### Get all items

```http
  GET /api/items
```

| Parameter | Type     | Description                |
| :-------- | :------- | :------------------------- |
| `api_key` | `string` | **Required**. Your API key |

#### Get item

```http
  GET /api/items/${id}
```

| Parameter | Type     | Description                       |
| :-------- | :------- | :-------------------------------- |
| `id`      | `string` | **Required**. Id of item to fetch |

#### add(num1, num2)

Takes two numbers and returns the sum.


## Features

- Convert any PDF file to a video file.
- Support for various video formats (e.g., MP4, AVI, MKV).
- Customizable video settings (e.g., resolution, frame rate).
- Option to add background music or narration.
- Text-to-speech feature to convert PDF text to spoken audio in the video.
- User-friendly interface for easy operation.
- Batch processing support to convert multiple PDFs at once.
## Installation

Clone the repository:

```bash
git clone https://github.com/your-username/pdftoVideoConverter.git
cd pdftoVideoConverter
```
Install the required Python packages:

```bash
poetry shell
```
```bash
poetry install
```
```bash
fastapi dev
```

