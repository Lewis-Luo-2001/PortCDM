class Config:
    def __init__(self):
        self.url = 'https://sdci.kh.twport.com.tw/khbweb/UA1007.aspx'
        self.output_html_path = 'output/output.html'
        self.output_csv_path = 'output/output.csv'
        self.ship_content_id_prefix = 'ASPx_船舶即時動態_tccell'
        self.cols = [
            "船編航次", "船名", "最新事件", "進港申請", "移泊申請", "出港申請",
            "港外船舶進港", "錨泊中", "進港作業中", "裝卸須知", "移泊作業中",
            "移泊裝卸作業", "出港作業中", "船舶已出港"
        ]
        self.event_url = 'https://sdci.kh.twport.com.tw/khbweb/UA3007.aspx'
        self.event_cols = [
            "事件來源", "發生時間", "事件名稱", "航行狀態", "引水單序號",
            "碼頭代碼", "事件內容"
        ]
