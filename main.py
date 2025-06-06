from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
import os
from typing import List, Optional

app = FastAPI(title="CSV Management API", version="1.0.0")  # ← This must be here!

# CSV file path
CSV_FILE = "data.csv"

# Pydantic models
class Item(BaseModel):
    id: int
    nome: str
    cognome: str
    codice_fiscale: str

class ItemCreate(BaseModel):
    nome: str
    cognome: str
    codice_fiscale: str

class ItemUpdate(BaseModel):
    nome: Optional[str] = None
    cognome: Optional[str] = None
    codice_fiscale: Optional[str] = None

# Initialize CSV file if it doesn't exist
def init_csv():
    if not os.path.exists(CSV_FILE):
        df = pd.DataFrame(columns=['id', 'nome', 'cognome', 'codice_fiscale'])
        df.to_csv(CSV_FILE, index=False)

# Helper functions
def read_csv():
    init_csv()
    return pd.read_csv(CSV_FILE)

def write_csv(df):
    df.to_csv(CSV_FILE, index=False)

def get_next_id():
    df = read_csv()
    if df.empty:
        return 1
    return int(df['id'].max()) + 1

# API Endpoints

@app.post("/items/", response_model=Item)
async def create_item(item: ItemCreate):
    """Create a new record"""
    df = read_csv()
    
    # Check if codice_fiscale already exists
    if not df.empty and item.codice_fiscale in df['codice_fiscale'].values:
        raise HTTPException(status_code=400, detail="Codice fiscale already exists")
    
    new_id = get_next_id()
    new_item = {
        'id': new_id,
        'nome': item.nome,
        'cognome': item.cognome,
        'codice_fiscale': item.codice_fiscale
    }
    
    df = pd.concat([df, pd.DataFrame([new_item])], ignore_index=True)
    write_csv(df)
    
    return Item(**new_item)

@app.get("/items/", response_model=List[Item])
async def get_all_items():
    """Retrieve all records"""
    df = read_csv()
    if df.empty:
        return []
    
    return [Item(**row.to_dict()) for _, row in df.iterrows()]

@app.get("/items/{item_id}", response_model=Item)
async def get_item(item_id: int):
    """Retrieve a single record by ID"""
    df = read_csv()
    
    if df.empty:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item_row = df[df['id'] == item_id]
    if item_row.empty:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return Item(**item_row.iloc[0].to_dict())

@app.put("/items/{item_id}", response_model=Item)
async def update_item(item_id: int, item_update: ItemUpdate):
    """Update an existing record"""
    df = read_csv()
    
    if df.empty:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item_index = df[df['id'] == item_id].index
    if len(item_index) == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Check if new codice_fiscale already exists (if being updated)
    if item_update.codice_fiscale:
        existing_cf = df[(df['codice_fiscale'] == item_update.codice_fiscale) & (df['id'] != item_id)]
        if not existing_cf.empty:
            raise HTTPException(status_code=400, detail="Codice fiscale already exists")
    
    # Update fields
    idx = item_index[0]
    if item_update.nome is not None:
        df.at[idx, 'nome'] = item_update.nome
    if item_update.cognome is not None:
        df.at[idx, 'cognome'] = item_update.cognome
    if item_update.codice_fiscale is not None:
        df.at[idx, 'codice_fiscale'] = item_update.codice_fiscale
    
    write_csv(df)
    
    return Item(**df.iloc[idx].to_dict())

@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    """Delete an existing record"""
    df = read_csv()
    
    if df.empty:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item_exists = df[df['id'] == item_id]
    if item_exists.empty:
        raise HTTPException(status_code=404, detail="Item not found")
    
    df = df[df['id'] != item_id]
    write_csv(df)
    
    return {"message": "Item deleted successfully"}

@app.get("/items/count")
async def get_items_count():
    """Get the number of rows in the CSV"""
    df = read_csv()
    return {"count": len(df)}

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "CSV Management API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)