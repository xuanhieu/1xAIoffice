# SPDX-License-Identifier: MPL-2.0
"""Chuỗi tuỳ chọn để Calc mở tệp CSV một cách an toàn (thuần Python, không cần UNO).

Mở CSV theo mặc định làm hỏng dữ liệu Việt Nam rất hay gặp: số điện thoại "0912..." mất số 0 đầu, số căn cước thành
số khoa học, "1/2" thành ngày tháng, và ô bắt đầu bằng "=" được chạy như công thức. Chuỗi dưới đây bắt Calc đọc mọi
cột thành CHỮ, nhận UTF-8 và không chạy công thức.

Định dạng chuỗi theo tài liệu bộ lọc Text CSV của LibreOffice: các giá trị ngăn bởi dấu phẩy, theo đúng thứ tự.
"""
UTF8 = 76            # mã bộ ký tự UTF-8 trong bộ lọc CSV
TEXT_COLUMN = 2      # mã "cột kiểu chữ"
MAX_COLUMNS = 1024   # Calc đọc tối đa 1024 cột


def column_formats(columns=MAX_COLUMNS):
    """"1/2/2/2/3/2/..." — mỗi cột một cặp <số cột>/<kiểu>, kiểu 2 là chữ."""
    return "/".join(f"{index}/{TEXT_COLUMN}" for index in range(1, columns + 1))


def filter_options(separator=",", quote='"', first_line=1, language=0, columns=MAX_COLUMNS):
    """Chuỗi FilterOptions cho bộ lọc "Text - txt - csv (StarCalc)".

    Thứ tự: dấu ngăn, dấu bao chuỗi, bộ ký tự, dòng đầu, kiểu từng cột, ngôn ngữ, ô trong dấu bao là chữ,
    nhận dạng số đặc biệt, giữ nguyên nội dung khi lưu, xuất công thức, bỏ khoảng trắng, xuất trang tính,
    tính công thức khi mở.
    """
    if not separator:
        raise ValueError("thiếu dấu ngăn cột")
    separators = ord(separator[0]) if len(separator) == 1 else "/".join(str(ord(c)) for c in separator)
    return ",".join(str(value) for value in (
        separators,
        ord(quote) if quote else "",
        UTF8,
        first_line,
        column_formats(columns),
        language,
        "true",      # ô nằm trong dấu bao được giữ nguyên là chữ
        "false",     # KHÔNG nhận dạng số đặc biệt: giữ "1/2" là chữ, không thành ngày
        "false",     # (chỉ dùng khi lưu) giữ nguyên nội dung như đang hiện
        "false",     # (chỉ dùng khi lưu) xuất công thức
        "false",     # không bỏ khoảng trắng ở hai đầu ô
        "false",     # (chỉ dùng khi lưu) xuất mọi trang tính
        "false",     # KHÔNG tính công thức khi mở: ô bắt đầu bằng "=" vẫn là chữ
    ))


def guess_separator(first_line):
    """Đoán dấu ngăn cột từ dòng đầu: dấu nào xuất hiện nhiều nhất ngoài dấu bao chuỗi."""
    counts = {}
    inside = False
    for ch in first_line:
        if ch == '"':
            inside = not inside
        elif not inside and ch in ",;\t|":
            counts[ch] = counts.get(ch, 0) + 1
    return max(counts, key=counts.get) if counts else ","


def looks_like_header(first_row, second_row):
    """Dòng đầu của tệp CSV có phải là dòng tiêu đề không? (thuần Python, có test riêng)

    Nhiều tệp CSV không có tiêu đề — dòng đầu đã là dữ liệu. Tô đậm và ghim nhầm dòng dữ liệu thì khó chịu hơn
    là không làm gì, nên chỉ nhận khi có đủ hai dấu hiệu:

      * mọi ô ở dòng đầu đều có chữ và KHÔNG ô nào là số (tiêu đề không ai đặt tên cột là "1234");
      * có ít nhất một ô ở dòng thứ hai là số, tức hai dòng khác kiểu nhau.

    Tệp chỉ có một dòng, hoặc cả hai dòng đều toàn chữ (danh sách tên chẳng hạn), đều trả về False.
    """
    if not first_row or not second_row:
        return False
    if any(not str(cell).strip() for cell in first_row):
        return False
    if any(_is_number(cell) for cell in first_row):
        return False
    return any(_is_number(cell) for cell in second_row)


def _is_number(cell):
    """Ô này đọc được thành số không? Nhận cả dấu phẩy thập phân và dấu chấm phân nhóm kiểu Việt Nam."""
    text = str(cell).strip().replace(" ", "")
    if not text:
        return False
    # 1.234,56 (kiểu Việt Nam) và 1,234.56 (kiểu Anh Mỹ) đều quy về dạng máy đọc được.
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".") if text.rfind(",") > text.rfind(".") else text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    elif text.count(".") > 1:
        text = text.replace(".", "")      # 1.250.000 kiểu Việt Nam; một dấu chấm thì để nguyên vì float đọc được
    try:
        float(text)
    except ValueError:
        return False
    return True
