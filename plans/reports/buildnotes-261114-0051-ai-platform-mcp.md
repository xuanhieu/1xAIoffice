# Sổ ghi phiên chạy đêm 14/11/2026 — nền tảng AI, mốc M3 trở đi

Phiên không có người canh. Ghi lại mọi default đã tự chọn, lý do, và chỗ sửa nếu chủ dự án muốn khác.

## Việc đang làm

Tiếp giai đoạn 8 theo đúng thứ tự mốc trong `plans/261112-1434-1xvnoffice/ai-platform-design.md` mục 17:
M3 (MCP client) → M4 (MCP server) → M5 (skill), làm được tới đâu commit tới đó.

## Default đã tự chọn

| # | Việc | Default đã chọn | Lý do | Sửa ở đâu |
|---|---|---|---|---|
| 1 | Làm mốc nào tiếp | M3 (MCP client) | Câu hỏi cuối của phiên trước chưa được trả lời. Thứ tự M3 → M4 → M5 là thứ tự chủ dự án đã duyệt trong bản thiết kế, nên theo đó thay vì tự đổi | — |
| 2 | Thư viện MCP | Tự viết client JSON-RPC tối giản bằng thư viện chuẩn, **không** vendor SDK `mcp` | Vendor SDK phải tải gói từ mạng về kho, là việc thêm phụ thuộc mà chủ dự án chưa duyệt. Giao thức MCP là JSON-RPC 2.0, đủ đơn giản để tự làm và tự kiểm. Khi nào chủ dự án duyệt thì đổi sang SDK chính thức | `extensions/1xvn-tools/agenthost/mcpclient.py` |
| 3 | Kiểu kết nối MCP ở M3 | Chỉ **stdio** | Bản thiết kế liệt kê stdio và Streamable HTTP. stdio không mở cổng mạng nên rủi ro thấp hơn, và đủ để đạt tiêu chí "gọi một MCP stdio". HTTP + OAuth để chủ dự án duyệt sau | cùng tệp |
| 4 | Quyền công cụ MCP | Mặc định **hỏi**, chưa cho phép thì **từ chối**; lưu lựa chọn theo từng công cụ | Bản thiết kế mục 7: lần đầu dùng phải hỏi. Mặc định từ chối là phía an toàn khi chạy không người canh | `mcp_tools.json` trong hồ sơ người dùng |
| 5 | Số bước gọi công cụ | Tối đa 8 bước mỗi yêu cầu, hạn giờ 120 giây | Bản thiết kế nói 12 bước, 5 phút. Hạ xuống cho bản đầu để một vòng lặp hỏng không treo lâu; nới lại khi chạy ổn | `agenthost/host.py`, hằng số `MAX_TOOL_STEPS` |
| 6 | Kích thước kết quả MCP | Cắt ở 20.000 ký tự mỗi kết quả | Chống máy chủ MCP trả kết quả khổng lồ làm tốn token và tiền của người dùng | `mcpclient.py`, hằng số `MAX_RESULT_CHARS` |

## Việc KHÔNG tự làm, chờ chủ dự án quyết

1. **Chưa gọi thử nhà cung cấp AI thật nào.** Toàn bộ kiểm thử dùng máy chủ giả chạy trên `127.0.0.1`. Cần chủ dự án gắn khoá thật (hoặc chạy Ollama cục bộ) mới biết chắc hình dạng yêu cầu và trả lời khớp thực tế.
2. **Không vendor thư viện ngoài** (`mcp`, `httpx`, `keyring`, `jsonschema`) vì phải tải gói về kho.
3. **Không mở cổng mạng nào.** MCP server của 1xVnOffice ở M4 chỉ làm bản stdio; bản HTTP nghe ở 127.0.0.1 kèm token để sau.

## M3 đã xong (14/11/2026)

Commit `9ec820f`, đã đẩy lên `main`. Tiêu chí "gọi một MCP stdio" đạt; phần HTTP + OAuth vẫn chờ chủ dự án duyệt (default #3).

Thêm hai default nhỏ trong lúc làm:

| # | Việc | Default đã chọn | Lý do | Sửa ở đâu |
|---|---|---|---|---|
| 7 | Lệnh trên menu cho MCP | Một lệnh **chỉ đọc** "Công cụ AI (MCP)…" liệt kê máy chủ, công cụ và trạng thái quyền | Người dùng cần nhìn thấy mình đã cho phép những gì trước khi mô hình dùng. Lệnh không chạy công cụ nào nên không có rủi ro | `onex_tools.py`, `cmd_McpTools` |
| 8 | Đường dẫn tệp cấu hình | `mcp_servers.json` và `mcp_tools.json` trong hồ sơ người dùng, có thể trỏ chỗ khác bằng `ONEX_MCP_SERVERS_PATH` / `ONEX_MCP_TOOLS_PATH` | Giống cách `providers.json` đang làm; biến môi trường để bài kiểm tự động không đụng vào hồ sơ thật | `onex_tools.py`, `_profile_file` |

### Một lỗi chỉ lộ ra khi chạy trên app thật

Vòng gọi công cụ đạt hết test trong tiến trình nhưng **chết ở bước đầu trên app**: app chạy Agent Host bằng `python -I host.py`, mà cờ `-I` bỏ thư mục của script khỏi `sys.path`, nên `import mcpclient` hỏng. Đã sửa bằng `_add_own_dir()` trong `host.py` và thêm một test chạy host.py như tiến trình riêng, đúng cách app gọi. Ghi lại vì đây là kiểu lỗi mà chỉ bài kiểm trên app thật mới thấy.

## M4 đã xong (14/11/2026)

Commit `864899f`, đã đẩy lên `main`. Tiêu chí "Claude Desktop sửa được tài liệu đang mở" đạt ở bản stdio.

| # | Việc | Default đã chọn | Lý do | Sửa ở đâu |
|---|---|---|---|---|
| 9 | Máy chủ MCP bật hay tắt sẵn | **Tắt sẵn**, người dùng bật bằng một lệnh trên menu | Bản thiết kế mục 8 và bảng mục 14 đều để tắt sẵn cho cả ba hồ sơ. Chạy không người canh thì càng phải để tắt | `mcp_server.json` trong hồ sơ người dùng |
| 10 | Đường nối | **UNO pipe cục bộ**, không mở cổng mạng nào | Đúng ràng buộc "không mở cổng mạng" đã ghi ở trên. Pipe là socket của riêng tài khoản người dùng trên máy này | `onex_tools.py`, `_start_acceptor` |
| 11 | Ghép đôi trợ lý | Trợ lý lạ bị **từ chối** và tên được ghi vào `mcp_clients.json` mục `pending`; người dùng duyệt ở lệnh trên menu | Không có hộp thoại nào bật lên từ một tiến trình ngoài; người dùng quyết trong app, lúc họ chủ động mở lệnh | `mcpserver/server.py`, `remember_pending` |
| 12 | Bộ công cụ mở ra ngoài | 9 công cụ (đọc tài liệu, cây tiêu đề, kiểm NĐ30, đọc vùng bảng tính, chèn, thay đoạn, chuyển mã, chuẩn hoá) | Bản thiết kế mục 6 liệt kê 17 công cụ; phần còn lại (biểu đồ, trình chiếu, xuất PDF, ký số) đụng tới xuất file và ký số nên để chủ dự án duyệt | `pythonpath/vn1x/doctools.py` |

Chưa làm ở M4, chờ chủ dự án quyết: bản nối **HTTP 127.0.0.1 + token**, **resources** (`1x://doc/<id>`), **prompts** (mở skill ra thành MCP prompt), và các công cụ `file.export_pdf` / `sign.request`.

## M5 đã xong (14/11/2026)

Commit `9147b8d`, đã đẩy lên `main`. Tám skill đi kèm theo đúng danh sách ở mục 9.2 của bản thiết kế.

| # | Việc | Default đã chọn | Lý do | Sửa ở đâu |
|---|---|---|---|---|
| 13 | Đọc front matter | Tự viết bộ đọc YAML tối giản (đủ cho chuỗi, danh sách, ánh xạ một tầng, true/false) | Thêm `pyyaml` là thêm phụ thuộc phải tải về kho, chưa được duyệt. Front matter của skill chỉ dùng đúng mấy dạng này | `pythonpath/vn1x/skills.py` |
| 14 | Thư mục `scripts/` của skill | **Chưa chạy** | Skill tải về từ mạng mà chạy được lệnh trên máy người dùng là rủi ro lớn nhất của cả mục 9, mà kho skill có duyệt và chữ ký thì chưa có. Front matter vẫn khai được `process` để sau này bật | cùng tệp |
| 15 | Công cụ skill được dùng | Không khai `tools` thì **không** được dùng công cụ nào | Khai rõ mới được, không ngầm hiểu. Khớp với cách quyền MCP đang làm | `skills.allowed_tools` |
| 16 | Lệnh chạy skill | **Chỉ đọc**: trả lời bằng hộp thông báo, không tự sửa tài liệu | Mốc này chưa có đường cho skill tự gọi công cụ ghi; muốn sửa thì dùng lệnh Viết lại bằng AI (đã có xem trước và hoàn tác) | `onex_tools.py`, `cmd_AiSkill` |
| 17 | Tiêu chí nghiệm thu của M5 | Chưa chạy được: bản thiết kế đòi `/cong-van` tạo công văn **đạt kiểm thể thức** | Cần một mô hình thật. Mọi kiểm thử đêm nay dùng nhà cung cấp giả nên chỉ chứng minh được đường đi, không chứng minh được chất lượng văn bản | chờ chủ dự án gắn khoá thật |

### Còn thiếu so với mục 9.2

Gọi skill bằng `/` trong khung trợ lý và bằng ô lệnh Alt+Q: chưa có, vì chưa có khung trợ lý dạng sidebar. Hiện gọi qua lệnh trên menu và nút Skill trên ribbon. Mở skill thành MCP prompt (mục 8) cũng chưa làm, nằm cùng phần resources/prompts còn thiếu của M4.

## Gắn tài khoản AI: nhiều loại khoá API và đăng nhập OAuth (14/11/2026)

Theo yêu cầu "gắn đa dạng api key lẫn oauth". Lệnh mới **Tài khoản AI (khoá API hoặc đăng nhập)...** trên menu Tiếng Việt, danh mục 18 nhà cung cấp cài sẵn, ba cách gắn: khoá API, đăng nhập OAuth, hoặc máy chủ chạy ngay trên máy.

| # | Việc | Default đã chọn | Lý do | Sửa ở đâu |
|---|---|---|---|---|
| 18 | Luồng OAuth | **Mã uỷ quyền + PKCE**, nhận mã ở cổng loopback `127.0.0.1` dựng tạm; **mã thiết bị** là đường dự phòng | Hai luồng duy nhất không cần client secret, đúng cho ứng dụng cài trên máy. Mã thiết bị cần cho máy không mở được trình duyệt và cho người muốn đăng nhập bằng điện thoại | `pythonpath/vn1x/oauth.py`, `agenthost/oauthflow.py` |
| 19 | `client_id` | **Không nhúng sẵn của ai cả**; người dùng dán client_id của chính họ | client_id gắn với một ứng dụng đã đăng ký; cơ quan thường tự đăng ký ứng dụng nội bộ. Nhúng client_id của người khác vừa sai vừa khoá người dùng vào một bên | `aiproviders.PRESETS`, trường `needs` |
| 20 | Chỗ cất thẻ và khoá | Keychain, một mục cho mỗi tài khoản, giá trị đưa vào qua **đầu vào chuẩn** của lệnh `security` | Truyền qua tham số dòng lệnh thì giá trị hiện trong danh sách tiến trình của máy. `providers.json` chỉ giữ `secret_ref` (tên mục) | `oauthflow.write_bundle`, `onex_tools._store_secret` |
| 21 | Gia hạn thẻ | Tự xin thẻ mới khi còn **2 phút** là hết hạn; giữ lại refresh token cũ nếu lần gia hạn không trả về cái mới | Hết hạn giữa chừng một câu hỏi dài thì hỏng cả lượt. Google không gửi lại refresh token ở lần gia hạn, mất nó là người dùng phải đăng nhập lại | `oauth.REFRESH_MARGIN_SECONDS`, `oauth.merge` |
| 22 | Danh sách mô hình | Hỏi thẳng nhà cung cấp (`action: "models"`) thay vì chép cứng tên mô hình vào app | Tên mô hình đổi liên tục; danh sách chép cứng sẽ sai sau vài tháng. Azure OpenAI không liệt kê được (mô hình là tên deployment) nên hỏi người dùng gõ | `agenthost/host.py`, `list_models` |
| 23 | Hình dạng API mới | Thêm `azure` (deployment + `api-version`); Vertex AI dùng `model_path` riêng | Hai chỗ này là nơi cơ quan hay đã có hợp đồng sẵn, không ép họ đổi nhà cung cấp | `host.build_request`, `aiproviders.fill` |
| 24 | Header xác thực | Khoá API theo kiểu riêng của từng hãng (`x-api-key`, `x-goog-api-key`, `api-key`, `Bearer`); thẻ OAuth **luôn** là `Authorization: Bearer` | Một chỗ quyết định, không rải if-else khắp nơi | `host._auth_headers` |
| 25 | Cấu hình cũ | Không có trường `auth` thì suy ra đúng như bản trước (máy chủ cục bộ và máy chủ OpenAI tự dựng không đòi khoá; dịch vụ đám mây thì đòi) | `providers.json` người dùng đã viết tay phải chạy tiếp, không bắt sửa | `aiconfig.auth_mode` |
| 26 | Hộp nhập khoá | Hộp **che chữ** ngay trong app, không bắt người dùng ra Terminal | Ra Terminal gõ lệnh là rào cản thật với cán bộ văn phòng. Giá trị vẫn không in ra đâu cả | `onex_tools._ask_text(secret=True)` |

### Đã kiểm

- 325 test logic (trước 315... trước loạt này là 253), độ phủ logic tiếng Việt 97,4% (yêu cầu ≥ 90%), `check-repo.py` đạt.
- 108 bước kiểm trên app thật (trước 94), trong đó 17 bước mới của phần `accounts`: gắn máy chủ nội bộ và lấy danh sách mô hình từ chính máy chủ; gắn khoá API và khẳng định khoá **không** nằm trong `providers.json` mà nằm trong kho bí mật; đăng nhập OAuth bằng mã thiết bị; rồi hỏi AI và khẳng định thẻ tới nhà cung cấp dưới dạng `Authorization: Bearer`.
- Mọi kiểm thử dùng nhà cung cấp AI giả và máy chủ đăng nhập giả trên `127.0.0.1`, kho khoá và kho thẻ trỏ sang tệp tạm. Không ra Internet, không chạm Keychain thật, không cần khoá thật.

### Vẫn chờ chủ dự án

Vẫn chưa gọi thử một nhà cung cấp AI thật nào, nên tiêu chí nghiệm thu của M5 (mục 17 ở trên) vẫn treo. Phần OAuth cũng mới chỉ chạy trước máy chủ giả: luồng mở trình duyệt thật và một client_id thật (Google hoặc Entra ID) chưa ai thử.
