import io

from PIL import Image
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from resizeimage.resizeimage import resize_contain

from defusedxml.cElementTree import parse as safe_parse

from mainsite.utils import verify_svg, scrubSvgElementTree


def _decompression_bomb_check(image, max_pixels=Image.MAX_IMAGE_PIXELS):
    pixels = image.size[0] * image.size[1]
    return pixels > max_pixels


class ResizeUploadedImage(object):

    def save(self, force_resize=False, *args, **kwargs):
        if (self.pk is None and self.image) or force_resize:
            try:
                image = Image.open(self.image)
                if _decompression_bomb_check(image):
                    raise ValidationError("Invalid image")
            except IOError:
                return super(ResizeUploadedImage, self).save(*args, **kwargs)

            if image.format == 'PNG':
                max_square = getattr(settings, 'IMAGE_FIELD_MAX_PX', 400)

                smaller_than_canvas = \
                    (image.width < max_square and image.height < max_square)

                if smaller_than_canvas:
                    max_square = (image.width
                                  if image.width > image.height
                                  else image.height)

                new_image = resize_contain(image, (max_square, max_square))

                byte_string = io.BytesIO()
                new_image.save(byte_string, 'PNG')

                self.image = InMemoryUploadedFile(byte_string, None,
                                                  self.image.name, 'image/png',
                                                  byte_string.tell(), None)

        return super(ResizeUploadedImage, self).save(*args, **kwargs)


class ScrubUploadedSvgImage(object):

    def save(self, *args, **kwargs):
        if self.image and verify_svg(self.image.file):
            self.image.file.seek(0)

            tree = safe_parse(self.image.file)
            scrubSvgElementTree(tree.getroot())

            buf = io.BytesIO()
            tree.write(buf)

            self.image = InMemoryUploadedFile(buf, 'image', self.image.name, 'image/svg+xml', buf.tell(), 'utf8')
        return super(ScrubUploadedSvgImage, self).save(*args, **kwargs)
