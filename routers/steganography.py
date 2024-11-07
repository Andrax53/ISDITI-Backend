from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException
from sqlalchemy.orm import Session
from .. import models, crud
from . import schemas
from ..database import SessionLocal, engine
from PIL import Image
import io
import os

models.Base.metadata.create_all(bind=engine)

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def genData(data: str) -> list:
    newd = [format(ord(i), '08b') for i in data]
    return newd

def modPix(pix, data) -> iter:
    datalist = genData(data)
    lendata = len(datalist)
    imdata = iter(pix)

    for i in range(lendata):
        pixels = [value for value in next(imdata)[:3] +
                                   next(imdata)[:3] +
                                   next(imdata)[:3]]

        for j in range(8):
            if datalist[i][j] == '0' and pixels[j] % 2 != 0:
                pixels[j] -= 1
            elif datalist[i][j] == '1' and pixels[j] % 2 == 0:
                if pixels[j] != 0:
                    pixels[j] -= 1
                else:
                    pixels[j] += 1

        if i == lendata - 1:
            if pixels[-1] % 2 == 0:
                if pixels[-1] != 0:
                    pixels[-1] -= 1
                else:
                    pixels[-1] += 1
        else:
            if pixels[-1] % 2 != 0:
                pixels[-1] -= 1

        pixels = tuple(pixels)
        yield pixels[0:3]
        yield pixels[3:6]
        yield pixels[6:9]

def encode_enc(newimg: Image.Image, data: str) -> None:
    w = newimg.size[0]
    (x, y) = (0, 0)

    for pixel in modPix(newimg.getdata(), data):
        newimg.putpixel((x, y), pixel)
        if x == w - 1:
            x = 0
            y += 1
        else:
            x += 1

@router.post("/encode/", response_model=schemas.Image)
async def encode(
    data: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Кодирует данные в загруженное изображение и сохраняет его.

    Параметры:
    - data: Строка данных, которую нужно закодировать в изображение.
    - file: Загруженный файл изображения.
    - db: Зависимость сессии базы данных.

    Возвращает:
    - Схема Image, содержащая информацию о изображении.
    """
    if not file.filename.lower().endswith(('.png', '.bmp')):
        raise HTTPException(
            status_code=400,
            detail="Unsupported image format. Please upload a PNG or BMP image."
        )

    contents = await file.read()
    try:
        image = Image.open(io.BytesIO(contents))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file.")

    if image.mode != 'RGB':
        image = image.convert('RGB')

    newimg = image.copy()

    try:
        encode_enc(newimg, data)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Error encoding data into the image."
        )

    new_img_name = f"encoded_{file.filename}"
    newimg.save(new_img_name)

    db_image = schemas.ImageCreate(filename=new_img_name, data=data)
    db_image = crud.create_image(db=db, image=db_image)

    return db_image

@router.get("/decode/{image_id}", response_model=schemas.DecodedData)
async def decode(image_id: int, db: Session = Depends(get_db)):
    """
    Декодирует данные из изображения, указанного по image_id.

    Параметры:
    - image_id: ID изображения в базе данных.
    - db: Зависимость сеанса базы данных.

    Возвращает:
    - Схема DecodedData, содержащая декодированные данные.
    """
    db_image = crud.get_image(db=db, image_id=image_id)
    if not db_image:
        raise HTTPException(status_code=404, detail="Image not found")

    if not os.path.exists(db_image.filename):
        raise HTTPException(
            status_code=404,
            detail="Image file not found on disk"
        )

    try:
        image = Image.open(db_image.filename)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Error opening image file."
        )

    imgdata = iter(image.getdata())
    data = ''

    while True:
        try:
            pixels = [value for value in next(imgdata)[:3] +
                                     next(imgdata)[:3] +
                                     next(imgdata)[:3]]
        except StopIteration:
            break

        binstr = ''
        for i in pixels[:8]:
            if i % 2 == 0:
                binstr += '0'
            else:
                binstr += '1'

        data += chr(int(binstr, 2))

        if pixels[-1] % 2 != 0:
            break

    return schemas.DecodedData(data=data)
