import os
from io import BytesIO
from PIL import Image
import requests
from fpdf import FPDF


class PDF(FPDF):
    def header(self):
        pass

    def chapter_title(self, title):
        self.set_font('Helvetica', 'B', 20)
        self.set_text_color(50, 50, 50)
        self.cell(0, 10, title, 0, 1, 'C')
        self.ln(10)

    def chapter_image(self, image_url):
        try:
            if image_url is not None and image_url.startswith('http'):
                response = requests.get(image_url)
                img = Image.open(BytesIO(response.content))
                img.save("temp_image.png")
                self.image("temp_image.png", x=0, y=20, w=210, h=277)  # Adjusted for title
                os.remove("temp_image.png")
            else:
                self.image("context/planing/meals/main/dishes.png", x=0, y=20, w=210, h=277)  # Adjusted for title
        except Exception as e:
            print(f"An error occurred while fetching the image: {e}")

    def chapter_body(self, body):
        self.set_font('Helvetica', '', 12)
        self.set_text_color(70, 70, 70)
        self.multi_cell(0, 10, body)
        self.ln()

    def section_separator(self):
        self.set_line_width(0.5)
        self.set_draw_color(180, 180, 180)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(10)
