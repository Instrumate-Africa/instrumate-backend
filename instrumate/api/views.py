import os
import re
import json
import sqlite3
import requests
import tempfile
import pymupdf
from django.conf import settings
from rest_framework import status
from nltk.tokenize import sent_tokenize
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from instrumate.settings import MODEL_URL



def clean_text(text):
        # Remove invisible characters
        text = re.sub(r'[\u200b\u200c\u200d\u200e\u200f]', '', text)
        # Normalize spacing, remove bullet points
        text = text.replace('•', '').strip()
        text = re.sub(r'[ \t]+', ' ', text)
        return text


def split_sentences(text):
    cleaned = clean_text(text)
    return sent_tokenize(cleaned)


def split_words(sentence):
    # Split the sentence into words using regex to handle punctuation
    words = re.findall(r'\b\w+\b', sentence)
    return words


def reconstruct_sentences(sentences: list[str]) -> str:
    result = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        # Capitalize first letter and add a period if missing
        sentence = sentence[0].upper() + sentence[1:]
        if not sentence.endswith(('.', '!', '?')):
            sentence += '.'
        result.append(sentence)
    return " ".join(result)


class HandleUpload(APIView):

    parser_classes = [MultiPartParser]
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.file_path = ""
        self.img_dir = ""
        self.image_paths = []
        self.chunks = {}
        self.page = {}
        self.translation = ""

    def file_chunker(self) -> None:
        document = pymupdf.open(self.file_path)
        self.chunks.clear()
        for page_no in range(0,document.page_count, 1):
            page = document.load_page(page_no)
            extracted_images = page.get_images()
            self.page["text"] = page.get_text()

            for index,img in enumerate(extracted_images):
                xref = img[0]
                pix = pymupdf.Pixmap(document, xref)
                img_filename = f"page{page_no}_img{index}.png"
                img_path = os.path.join(self.img_dir, img_filename)
                self.image_paths.append(os.path.join("/media/" , img_filename))

                if pix.n > 5:
                    pix = pymupdf.Pixmap(pymupdf.csRGB, pix)

                pix.save(img_path)
                pix=None

            if self.image_paths:
                self.page["images"] = self.image_paths.copy()
            else:
                self.page["images"] = []
            self.image_paths.clear()

            self.page["symbols"] = []
            self.chunks[page_no] = self.page.copy()
            self.page.clear()

    def post(self, request):
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return Response({"error": "No uploaded file detected!"}, status=status.HTTP_400_BAD_REQUEST)

        self.file_path = uploaded_file.name

        tmp_dir  = tempfile.gettempdir()
        self.img_dir  = os.path.join(tmp_dir, "upload_dir/images")
        file_dir = os.path.join(tmp_dir, "upload_dir/files")
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
        self.file_path = os.path.join(file_dir, self.file_path)
        try:
            with open(self.file_path, "wb+") as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            # store chunks in redis
            self.file_chunker()
            sentences: list[str] = []
            for i in range(0, len(self.chunks),1):
                sentences += split_sentences(self.chunks[i]["text"])
            context = {
                "file_name": self.file_path,
                # "chunks": self.chunks,
                "sentences": sentences
            }

            return Response(context, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class Eng_To_KSL(APIView):
    def post(self, request):
        text = request.data.get("text", "")
        sentences = split_sentences(text)
        translation: str = ""
        translated_sentences: list[str] = []

        TRANSLATION_SERVICE_URL = f"{MODEL_URL}/translate/english-to-ksl"

        for sentence in sentences:
            try:
                response = requests.post(
                    TRANSLATION_SERVICE_URL,
                    json={"text": sentence},
                    timeout=10
                )

                if response.status_code == 200:
                    translation = response.json().get("translation")
                else:
                    translation = "[Translation Error]"
            except requests.exceptions.RequestException as e:
                return Response({"error": f"Translation service unreachable: {str(e)}"}, 
                                status=status.HTTP_503_SERVICE_UNAVAILABLE)

            translated_sentences.append(translation)

        full_translation = reconstruct_sentences(translated_sentences)
        translated_sentences = split_sentences(full_translation)

        words = []
        for sentence in translated_sentences:
            words.extend(split_words(sentence))

        return Response({
            "original_sentences": sentences,
            "translated_sentences": translated_sentences,
            "words": words
        }, status=status.HTTP_200_OK)


class KSL_To_Eng(APIView):
    def post(self, request):
        text = request.data.get("text", "")
        TRANSLATION_SERVICE_URL = f"{MODEL_URL}/translate/ksl-to-eng"
        try:
            response = requests.post(
                TRANSLATION_SERVICE_URL,
                json={"text": text},
                timeout=10
            )

            if response.status_code == 200:
                translation = response.json().get("content", {}).get("translation")
            else:
                translation = "[Translation Error]"
        except requests.exceptions.RequestException as e:
            return Response({"error": f"Translation service unreachable: {str(e)}"}, 
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response({"translation": translation}, status=status.HTTP_200_OK)


class Animations(APIView):
    def post(self, request):
        text = request.data.get("text")
        if text is None:
            return Response({"message": "Nothing to get animation data for:"} , status=status.HTTP_400_BAD_REQUEST)

        words: list[str] = text.split(" ") if isinstance(text, str) else text
        animation_data = []
        dataset_filepath = os.path.join(settings.BASE_DIR, "dataset.sqlite3.db")
        cxn = sqlite3.connect(dataset_filepath)
        cursor = cxn.cursor()
        placeholders = ", ".join(['?'] * len(words))
        query = f"SELECT ani_data FROM records WHERE name COLLATE NOCASE IN ({placeholders})"
        cursor.execute(query, words)
        data = cursor.fetchall()

        for d in data:
            blob = json.loads(str(d[0].decode('utf-8')))
            animation_data += blob

        cursor.close()
        cxn.close()
        return Response({"animation_data": animation_data}, status=status.HTTP_200_OK)
