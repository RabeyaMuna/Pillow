from __future__ import annotations

from io import BytesIO

import pytest

from PIL import CurImagePlugin, Image
from PIL._binary import o8
from PIL._binary import o16le as o16
from PIL._binary import o32le as o32

from .helper import assert_image_equal


def test_sanity() -> None:
    with Image.open("Tests/images/cur/deerstalker.cur") as im:
        assert im.size == (32, 32)
        assert im.info["hotspots"] == [(0, 0)]
        assert isinstance(im, CurImagePlugin.CurImageFile)

        # Check pixel colors to ensure image is loaded properly
        assert im.getpixel((10, 1)) == (0, 0, 0, 0)
        assert im.getpixel((11, 1)) == (253, 254, 254, 1)
        assert im.getpixel((16, 16)) == (84, 87, 86, 255)


def test_largest_cursor() -> None:
    magic = b"\x00\x00\x02\x00"
    sizes = ((1, 1), (8, 8), (4, 4))
    data = magic + o16(len(sizes))

    # Build images (DIBs) for each size and collect directory entries
    images = []
    for w, h in sizes:
        # Create a BITMAPINFOHEADER (40 bytes) for a 32bpp DIB.
        # For icons/cursors, the stored height is doubled (height * 2).
        dib = (
            o32(40)  # header size
            + o32(w)  # width
            + o32(h * 2)  # height (icon stores height*2)
            + o16(1)  # planes
            + o16(32)  # bits per pixel
            + o32(0)  # compression (BI_RGB)
            + o32(w * h * 4)  # size image (raw pixels)
            + o32(0)  # x pixels per meter
            + o32(0)  # y pixels per meter
            + o32(0)  # colors used
            + o32(0)  # important colors
        )
        # Pixel data (zeroed) and AND mask (1-bit per pixel, padded to 32-bit boundaries per row)
        pixels = b"\x00" * (w * h * 4)
        mask_row_bytes = ((w + 31) // 32) * 4
        mask = b"\x00" * (mask_row_bytes * h)
        img = dib + pixels + mask
        images.append(img)

    # Compute offsets and write directory entries with valid size and offset fields
    offset = 6 + 16 * len(sizes)  # header (6 bytes) + directory entries
    entries = []
    for img, (w, h) in zip(images, sizes):
        size_in_res = len(img)
        # CUR directory entry layout: width(1), height(1), color count(1), reserved(1),
        # hotspot_x(2), hotspot_y(2), size_in_res(4), image_offset(4)
        entry = (
            o8(w)
            + o8(h)
            + o8(0)
            + o8(0)
            + o16(0)
            + o16(0)
            + o32(size_in_res)
            + o32(offset)
        )
        entries.append(entry)
        offset += size_in_res

    # Append directory entries and image data
    for entry in entries:
        data += entry
    for img in images:
        data += img

    with Image.open(BytesIO(data)) as im:
        assert im.size == (8, 8)


def test_posy_link() -> None:
    with Image.open("Tests/images/cur/posy_link.cur") as im:
        assert im.size == (128, 128)
        assert im.info["sizes"] == {(128, 128), (96, 96), (64, 64), (48, 48), (32, 32)}
        assert im.info["hotspots"] == [(25, 7), (18, 5), (12, 3), (9, 2), (5, 1)]

        # check pixel colors
        assert im.getpixel((0, 0)) == (0, 0, 0, 0)
        assert im.getpixel((20, 20)) == (0, 0, 0, 255)
        assert im.getpixel((40, 40)) == (255, 255, 255, 255)

        im.size = (32, 32)
        im.load()
        assert im.getpixel((0, 0)) == (0, 0, 0, 0)
        assert im.getpixel((10, 10)) == (191, 191, 191, 255)


def test_stopwtch() -> None:
    with Image.open("Tests/images/cur/stopwtch.cur") as im:
        assert im.size == (32, 32)
        assert im.info["hotspots"] == [(16, 19)]

        assert im.getpixel((16, 16)) == (0, 0, 255, 255)
        assert im.getpixel((8, 16)) == (255, 0, 0, 255)


def test_win98_arrow() -> None:
    with Image.open("Tests/images/cur/win98_arrow.cur") as im:
        assert im.size == (32, 32)
        assert im.info["hotspots"] == [(10, 10)]

        assert im.getpixel((0, 0)) == (0, 0, 0, 0)
        assert im.getpixel((16, 16)) == (0, 0, 0, 255)
        assert im.getpixel((14, 19)) == (255, 255, 255, 255)


def test_invalid_file() -> None:
    invalid_file = "Tests/images/cur/posy_link.png"

    with pytest.raises(SyntaxError):
        CurImagePlugin.CurImageFile(invalid_file)

    no_cursors_file = "Tests/images/cur/no_cursors.cur"

    cur = CurImagePlugin.CurImageFile("Tests/images/cur/deerstalker.cur")
    assert cur.fp is not None
    cur.fp.close()
    with open(no_cursors_file, "rb") as cur.fp:
        with pytest.raises(TypeError):
            cur._open()


def test_save_win98_arrow() -> None:
    with Image.open("Tests/images/cur/win98_arrow.png") as im:
        # save the data
        with BytesIO() as output:
            im.save(
                output,
                format="CUR",
                sizes=[(32, 32)],
                hotspots=[(10, 10)],
                bitmap_format="bmp",
            )
            with Image.open(output) as reloaded:
                assert_image_equal(im, reloaded)

        with BytesIO() as output:
            im.save(output, format="CUR")

            # check default save params
            with Image.open(output) as reloaded:
                assert reloaded.size == (32, 32)
                assert reloaded.info["sizes"] == {(32, 32), (24, 24), (16, 16)}
                assert reloaded.info["hotspots"] == [(0, 0), (0, 0), (0, 0)]


def test_save_posy_link() -> None:
    sizes = [(128, 128), (96, 96), (64, 64), (48, 48), (32, 32)]
    hotspots = [(25, 7), (18, 5), (12, 3), (9, 2), (5, 1)]

    with Image.open("Tests/images/cur/posy_link.png") as im:
        # save the data
        with BytesIO() as output:
            im.save(
                output,
                sizes=sizes,
                hotspots=hotspots,
                format="CUR",
                bitmap_format="bmp",
            )

            # make sure saved output is readable
            # and sizes/hotspots are correct
            with Image.open(output, formats=["CUR"]) as reloaded:
                assert (128, 128) == reloaded.size
                assert set(sizes) == reloaded.info["sizes"]

        with BytesIO() as output:
            im.save(output, sizes=sizes[3:], hotspots=hotspots[3:], format="CUR")

            # make sure saved output is readable
            # and sizes/hotspots are correct
            with Image.open(output, formats=["CUR"]) as reloaded:
                assert reloaded.size == (48, 48)
                assert reloaded.info["sizes"] == set(sizes[3:])

            # check error is thrown when size and hotspot length don't match
            with pytest.raises(ValueError):
                im.save(
                    output,
                    sizes=sizes[2:],
                    hotspots=hotspots[3:],
                    format="CUR",
                    bitmap_format="bmp",
                )
