import boto3
import uuid
from io import BytesIO
from botocore.exceptions import ClientError
from typing import Optional

from utils.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET, AWS_REGION

s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

BUCKET_NAME = AWS_S3_BUCKET
SIGNED_URL_EXPIRY = 900  # 15 minutes


def sign_url(viz):
    s3_key = viz.html_code.split(f"{BUCKET_NAME}.s3.amazonaws.com/")[-1]
    signed_url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET_NAME, "Key": s3_key},
        ExpiresIn=SIGNED_URL_EXPIRY,
    )
    return signed_url, SIGNED_URL_EXPIRY


def create_and_upload_html(html_content: str, title: str, filename: str = None) -> str:
    if not filename:
        filename = f"{title.replace(' ', '_').lower()}-{uuid.uuid4()}.html"
    elif not filename.endswith(".html"):
        filename += ".html"

    html_file = BytesIO(html_content.encode("utf-8"))

    s3_client.upload_fileobj(
        html_file,
        BUCKET_NAME,
        filename,
        ExtraArgs={"ContentType": "text/html"},
    )

    return f"https://{BUCKET_NAME}.s3.amazonaws.com/{filename}"


def detect_style(description: str) -> Optional[str]:
    desc = description.lower()

    style_keywords = {
        "cyberpunk": ["neon", "city", "rain", "futuristic", "digital", "hologram"],
        "ethereal": ["mist", "dream", "floating", "soft", "spirit", "light", "crystal"],
        "industrial": ["machine", "metal", "rust", "factory", "engine", "gear"],
        "organic": ["forest", "nature", "growth", "biological", "plant", "living"],
        "cosmic": ["space", "star", "galaxy", "cosmic", "nebula", "universe"],
        "aquatic": ["water", "ocean", "bubble", "underwater", "sea"],
    }

    scores = {style: 0 for style in style_keywords}

    for style, keywords in style_keywords.items():
        for word in keywords:
            if word in desc:
                scores[style] += 1

    best_style = max(scores, key=scores.get)

    return best_style if scores[best_style] > 0 else None

