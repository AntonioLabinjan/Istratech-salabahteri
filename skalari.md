Skalar,Naziv,Što mjeri?,Algoritam / Logika,Raspon
1.,fuzzy_distance,Preklapanje cijelog teksta s obje strane,fuzz.token_set_ratio,0.0 do 1.0
2.,presence,Je li OCR uspješno našao/pročitao ime na obje strane?,1.0 (Ima na obje) / 0.0 (Fali na bar jednoj),0.0 ili 1.0
3.,match,Točnost podudaranja imena i prezimena,fuzz.token_sort_ratio (samo ako je presence=1.0),0.0 do 1.0
