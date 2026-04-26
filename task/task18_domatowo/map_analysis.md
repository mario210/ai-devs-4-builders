## Map Analysis Report

### Full Map Grid:
```text
   | A      | B      | C      | D     | E       | F      | G      | H      | I      | J       | K      
1  | tree   | road   | road   | road  | empty   | block3 | block3 | tree   | empty  | parking | parking
2  | tree   | tree   | empty  | road  | road    | block3 | block3 | tree   | road   | parking | parking
3  | empty  | empty  | empty  | road  | parking | empty  | empty  | tree   | road   | empty   | empty  
4  | block1 | block1 | empty  | road  | parking | school | school | school | road   | field   | field  
5  | block1 | block1 | empty  | road  | parking | school | school | school | road   | field   | field  
6  | road   | road   | road   | road  | road    | road   | road   | road   | road   | road    | empty  
7  | block2 | block2 | empty  | road  | empty   | church | church | church | empty  | tree    | empty  
8  | block2 | block2 | empty  | road  | empty   | church | church | church | empty  | tree    | empty  
9  | empty  | road   | road   | road  | road    | road   | road   | road   | road   | road    | empty  
10 | block3 | block3 | block3 | empty | tree    | empty  | empty  | block3 | block3 | tree    | empty  
11 | block3 | block3 | block3 | empty | tree    | empty  | empty  | block3 | block3 | tree    | empty  
```


### Identified Blocks (block1, block2, block3):
[
  "F1",
  "G1",
  "F2",
  "G2",
  "A4",
  "B4",
  "A5",
  "B5",
  "A7",
  "B7",
  "A8",
  "B8",
  "A10",
  "B10",
  "C10",
  "H10",
  "I10",
  "A11",
  "B11",
  "C11",
  "H11",
  "I11"
]

### Identified Roads (road):
[
  "B1",
  "C1",
  "D1",
  "D2",
  "E2",
  "I2",
  "D3",
  "I3",
  "D4",
  "I4",
  "D5",
  "I5",
  "A6",
  "B6",
  "C6",
  "D6",
  "E6",
  "F6",
  "G6",
  "H6",
  "I6",
  "J6",
  "D7",
  "D8",
  "B9",
  "C9",
  "D9",
  "E9",
  "F9",
  "G9",
  "H9",
  "I9",
  "J9"
]

### Block3 North:
[
  "F1",
  "F2",
  "G1",
  "G2"
]

### Block3 South-East:
[
  "H10",
  "H11",
  "I10",
  "I11"
]

### Block3 South-West:
[
  "A10",
  "A11",
  "B10",
  "B11",
  "C10",
  "C11"
]

### Tile Information:
{
  "road": {
    "label": "Ulica",
    "symbol": "UL"
  },
  "tree": {
    "label": "Drzewa",
    "symbol": "DR"
  },
  "house": {
    "label": "Dom",
    "symbol": "DM"
  },
  "empty": {
    "label": "Pusta przestrzen",
    "symbol": "  "
  },
  "block1": {
    "label": "Blok 1p",
    "symbol": "B1"
  },
  "block2": {
    "label": "Blok 2p",
    "symbol": "B2"
  },
  "block3": {
    "label": "Blok 3p",
    "symbol": "B3"
  },
  "church": {
    "label": "Kosciol",
    "symbol": "KS"
  },
  "school": {
    "label": "Szkola",
    "symbol": "SZ"
  },
  "parking": {
    "label": "Parking",
    "symbol": "PK"
  },
  "field": {
    "label": "Boisko",
    "symbol": "BS"
  }
}