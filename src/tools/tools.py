from langchain_core.tools import tool
from src.fake_data import FLIGHTS_DB, HOTELS_DB
from src.telemetry.logger import logger

def format_currency(amount: int) -> str:
    return f"{amount:,}₫".replace(",", ".")

@tool
def search_flights(origin: str, destination: str) -> str:
    """Tìm kiếm chuyến bay giữa hai thành phố. Trả về danh sách chuyến bay kèm giá."""
    try:
        # Thử tra cứu xuôi và ngược
        flights = FLIGHTS_DB.get((origin, destination)) or FLIGHTS_DB.get((destination, origin))
        
        if not flights:
            return f"Không tìm thấy chuyến bay giữa {origin} và {destination}."
        
        res = [f"Chuyến bay từ {origin} đến {destination}:"]
        for f in flights:
            res.append(f"- {f['airline']} ({f['class']}): {f['departure']} -> {f['arrival']} | Giá: {format_currency(f['price'])}")
        return "\n".join(res)
    except Exception as e:
        logger.error(f"Lỗi search_flights: {e}")
        return "Đã xảy ra lỗi khi tra cứu chuyến bay."

@tool
def search_hotels(city: str, max_price_per_night: any = 999999999) -> str:
    """
    Tìm kiếm khách sạn tại một thành phố cụ thể trong dữ liệu hệ thống .
    
    Tham số:
    - city: Tên thành phố (Ví dụ: 'Đà Nẵng', 'Phú Quốc', 'Hồ Chí Minh').
    - max_price_per_night: Ngân sách tối đa cho một đêm. 
      LƯU Ý: Phải là số nguyên đơn vị VNĐ (Ví dụ: 1500000). Không dùng đơn vị khác.
    """
    try:
        # Giải pháp triệt để 1: Ép kiểu dữ liệu (Type Casting)
        # LLM đôi khi gửi chuỗi "1500000", hàm int() sẽ xử lý được cả str và int
        max_price = int(float(max_price_per_night)) 

        # Giải pháp triệt để 2: Xử lý logic nghiệp vụ về đơn vị tiền tệ
        # Nếu LLM truyền giá trị quá nhỏ (ví dụ < 10000), khả năng cao nó đang hiểu nhầm là USD hoặc nghìn đồng
        if max_price < 10000 and max_price != 0:
            logger.warning(f"Cảnh báo: max_price {max_price} có vẻ quá thấp, LLM có thể sai đơn vị.")
            return f"Lỗi: Ngân sách {max_price}đ quá thấp. Vui lòng sử dụng đơn vị VNĐ (Ví dụ: 1.000.000)."

        hotels = HOTELS_DB.get(city)
        if not hotels:
            return f"Không tìm thấy khách sạn tại {city} trong cơ sở dữ liệu."
        
        # Lọc theo giá tối đa và sắp xếp theo rating giảm dần
        filtered = [h for h in hotels if h['price_per_night'] <= max_price]
        filtered.sort(key=lambda x: x['rating'], reverse=True)
        
        if not filtered:
            return f"Không tìm thấy khách sạn tại {city} với giá dưới {format_currency(max_price)}/đêm. Hãy thử tăng ngân sách."
        
        res = [f"Danh sách khách sạn tại {city} (Sắp xếp theo đánh giá cao nhất):"]
        for h in filtered:
            res.append(f"- {h['name']} ({h['stars']} sao): {format_currency(h['price_per_night'])}/đêm | Rating: {h['rating']} | Khu vực: {h['area']}")
        return "\n".join(res)

    except (ValueError, TypeError) as e:
        logger.error(f"Lỗi tham số đầu vào search_hotels: {e}")
        return "Lỗi: Giá trị ngân sách tối đa phải là một con số (Ví dụ: 2000000)."
@tool
def calculate_budget(total_budget: int, expenses: str) -> str:
    """Tính toán ngân sách còn lại. Expenses format: 'tên: số tiền, tên: số tiền'."""
    try:
        total_expense = 0
        expense_details = []
        # Parse chuỗi expenses
        items = [item.strip() for item in expenses.split(",")]
        for item in items:
            name, amount = item.split(":")
            amount_int = int(amount.strip())
            total_expense += amount_int
            expense_details.append(f"- {name.strip()}: {format_currency(amount_int)}")
            
        remaining = total_budget - total_expense
        
        report = ["--- Bảng chi phí ---"]
        report.extend(expense_details)
        report.append(f"Tổng chi: {format_currency(total_expense)}")
        report.append(f"Ngân sách ban đầu: {format_currency(total_budget)}")
        report.append(f"Còn lại: {format_currency(remaining)}")
        
        if remaining < 0:
            report.append(f"⚠️ CẢNH BÁO: Vượt ngân sách {format_currency(abs(remaining))}! Cần điều chỉnh.")
        
        return "\n".join(report)
    except Exception:
        return "Lỗi format expenses. Vui lòng dùng định dạng 'tên: số tiền, tên: số tiền'."