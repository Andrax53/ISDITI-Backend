from pydantic import BaseModel

class ImageBase(BaseModel):
    filename: str
    data: str

class ImageCreate(ImageBase):
    pass

class Image(ImageBase):
    id: int

    class Config:
        from_attributes = True

class DecodedData(BaseModel):
    data: str
