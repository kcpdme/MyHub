with open("app/routes/api.py", "r") as f:
    content = f.read()

import re

new_text = """@router.post("/inbox/{item_id}/archive")
def archive_inbox_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.TelegramInboxItem).filter(models.TelegramInboxItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inbox item not found")
    item.is_archived = True
    db.add(item)
    db.commit()
    return {"ok": True}


@router.post("/inbox/{item_id}/analyze")
def analyze_inbox_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.TelegramInboxItem).filter(models.TelegramInboxItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inbox item not found")
    
    # AI Classification Mock
    text_content = str(item.text).lower() + " " + item.item_type
    tags = ["[AI]"]
    if "photo" in text_content or "video" in text_content:
        tags.append("#media")
    if "http" in text_content or "www" in text_content:
        tags.append("#link")
    if "todo" in text_content or "need" in text_content or "buy" in text_content:
        tags.append("#actionable")
    if "invoice" in text_content or "$" in text_content or "receipt" in text_content or "bill" in text_content:
        tags.append("#finance")
    if "pass" in text_content or "code" in text_content:
        tags.append("#auth")
    if len(tags) == 1:
        tags.append("#general")
        
    tag_str = " ".join(set(tags))
    if not item.text:
        item.text = tag_str
    elif "[AI]" not in item.text:
        item.text = f"{item.text}\n\n{tag_str}"
        
    db.add(item)
    db.commit()
    return {"ok": True, "tags": tag_str}"""

content = content.replace("""@router.post("/inbox/{item_id}/archive")
def archive_inbox_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.TelegramInboxItem).filter(models.TelegramInboxItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inbox item not found")
    item.is_archived = True
    db.add(item)
    db.commit()
    return {"ok": True}""", new_text)

with open("app/routes/api.py", "w") as f:
    f.write(content)
