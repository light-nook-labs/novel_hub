from datetime import datetime, timedelta
import re

if __name__ == "__main__":
    # date_str = '2026/4/30 16:11:48'
    # now = datetime.now()
    # d = datetime.strptime(date_str, "%Y/%m/%d %H:%M:%S")
    # delta = timedelta(days=30)
    # print(now, d, delta, sep='\n')
    # print(now - d < delta)
    pattern = re.compile(r'(\d+)字\[(.+)\]')
    s = '50000字[连载中]'
    print(pattern.search(s).groups())
