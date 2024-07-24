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

    def _add_image_centered(self, image_path):
        # Load image using PIL to get its dimensions
        image = Image.open(image_path)
        image_width, image_height = image.size

        # Get the dimensions of the PDF page
        page_width = self.w
        page_height = self.h

        # Calculate the aspect ratio of the image
        aspect_ratio = image_width / image_height

        # Calculate the maximum width and height the image can have on the PDF page
        max_width = page_width - 20  # Subtract some margin
        max_height = page_height - 40  # Subtract some margin

        # Calculate the new width and height of the image to maintain the aspect ratio
        if max_width / aspect_ratio <= max_height:
            new_width = max_width
            new_height = max_width / aspect_ratio
        else:
            new_width = max_height * aspect_ratio
            new_height = max_height

        # Calculate the position to center the image
        x = (page_width - new_width) / 2
        y = (page_height - new_height) / 2

        # Add the image to the PDF
        self.image(image_path, x=x, y=y, w=new_width, h=new_height)

    def chapter_image(self, image_url):
        try:
            if image_url is not None and image_url.startswith('http'):
                response = requests.get(image_url)
                img = Image.open(BytesIO(response.content))
                img.save("temp_image.png")
                self._add_image_centered("temp_image.png")
                os.remove("temp_image.png")
            elif image_url is not None and os.path.exists(f"context/planing/meals/main/assets/{image_url}"):
                self._add_image_centered(f"context/planing/meals/main/assets/{image_url}")
            else:
                self._add_image_centered("context/planing/meals/main/generic_dishes.png")
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
