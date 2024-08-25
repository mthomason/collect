
from datetime import datetime
from collect.utility.listitem import UnorderedList, DescriptionList, TimeItem, IntItem, StrItem, LinkItem

if __name__ == '__main__':

	item_s = StrItem(title="Site", value="Hobby Report")
	item_l = StrItem(title="Link", value="https://hobbyreport.net")
	item_h = LinkItem(title="Link", value="https://hobbyreport.net")
	item_e = IntItem(title="Edition", value=99)
	item_u = TimeItem(title="Last Updated", value=datetime.now())
	dlitems = UnorderedList()
	dlitems.additem(item_s)
	dlitems.additem(item_l)
	dlitems.additem(item_h)
	dlitems.additem(item_e)
	dlitems.additem(item_u)
	print(dlitems.getstring())
	print(dlitems.gethtml())

	exit(0)

