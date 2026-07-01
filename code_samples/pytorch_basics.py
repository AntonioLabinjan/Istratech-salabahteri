import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

# ==========================================
# 0. DEVICE MANAGEMENT
# ==========================================
# Provjerimo dali je GPU dostupan
if torch.cuda.is_available():
    device = torch.device("cuda")
else:
    device = torch.device("cpu")

print(f"Using device: {device}\n")


# 1. namjerno definiramo dummy data, čisto da se kod izvrti
# x -> input data
# y -> pripadna klasa
X_dummy = torch.randn(100, 10)
y_dummy = torch.randint(0, 3, (100,)).long()

# spaja x i y data row by row da dobijemo smislene retke
dataset = TensorDataset(X_dummy, y_dummy)
# dataloader definira kako ćemo feedat podatke u trening
# params:
# - dataset -> s kojim podacima uopće radimo
# - batch_size -> koliko podatka ide u svaki chunk; ne želimo feedat 1 po 1 podatak jer bi bilo presporo
# - shuffle -> svaki put random mješamo podatke
dataloader = DataLoader(dataset, batch_size=16, shuffle=True)


# ==========================================
# 2. DEFINE THE MULTI-CLASS MODEL
# ==========================================
# definiramo arhitekturu našeg modela
# init omogućava da definiramo "prazni, glupi" model za početak
# da ne napravimo init, u svakoj epohi bi se stari model prebrisao i nastao bi potpuno novi
class MultiClassClassifier(nn.Module):
    def __init__(self, input_dim, num_classes):
        super(MultiClassClassifier, self).__init__()
        # sloj od 8 neurona od kojih je svaki povezan sa svakim od neurona u idućem sloju
        # linearni sloj
        self.hidden = nn.Linear(input_dim, 8)

        # sam linearni sloj bi crtao "ravne linije" među klasama
        # koristimo ReLU koji radi max(0, x)
        # negativni input pretvara u nulu, pozitivni input ostavlja kako je
        self.relu = nn.ReLU()

        # output sloj
        # vektor s 3 vrijednosti
        # raw score za svaku klasu (npr. 12, 56, 4)
        self.output = nn.Linear(8, num_classes)

    # funkcija koja odrađuje forward pass
    # uzima vrijednost i radi operacije nad njom
    def forward(self, x):
        # prvi korak => Wx + b; linearni klasifikator
        x = self.hidden(x)
        # drugi korak => na rezultate linearnog klasifikatora primjenjuje relu (max(0,x))
        x = self.relu(x)
        # treći korak => rezultate sprema za output (3 vrijednosti)
        x = self.output(x)
        return x

# Initialize model
# doslovno napravimo instancu klase koju smo gore definirali s input parametrima dimenzije 10 i outputom 3 klase
model = MultiClassClassifier(input_dim=10, num_classes=3)

# mapiramo trening na grafičku karticu
model = model.to(device)


# ==========================================
# 3. LOSS FUNCTION AND OPTIMIZER
# ==========================================
# ova varijabla definira kako mjerimo grešku u treningu
# crossentropy loss interno pretvara sirove rezultate iz output vektora u vjerojatnosti (postotke)
# što je predikcija točnija, loss je manji
criterion = nn.CrossEntropyLoss()

# optimizer pametno "nadzire" trening za nas
# koristi stohastic gradient descent
# uzima mali batch podataka u svakom koraku

# računa kako prilagoditi weightove modela => weightovi su basically znanje modela
# traži točku u kojoj model najmanje griješi i najbolje predviđa
# learning rate predstavlja za koliko će se model pomicati, odnosno koliki korak će imati
optimizer = optim.SGD(model.parameters(), lr=0.05)


# ==========================================
# 4. THE TRAINING LOOP
# ==========================================
# epoha => kompletan prolazak kroz podatke
# 5 puta čisto za POC, ali svakako treba više za bolji trening
epochs = 5

print("Starting Training...")
# petlja koja iterira kroz podatke onoliko puta koliko imamo epoha
for epoch in range(epochs):
   # inicijaliziramo loss, broj točnih predikcija i broj ukupnih primjeraka na 0
   # iz predicitions i samples kasnije računamo metrike
    running_loss = 0.0
    correct_predictions = 0
    total_samples = 0
    
    for batch_X, batch_y in dataloader:
        # CRITICAL: Both your features and your targets MUST be on the same device as the model
        # 2 batcha podataka
        # x => input podaci
        # y => točne klase
        batch_X = batch_X.to(device)
        batch_y = batch_y.to(device)
        
        # Zero out gradients from the previous step
        # svaki put resetiramo gradijent, jer ne želimo da model zbraja optimizacijske korake iz prethodne epohe
        # to bi se onda akumuliralo u nešto besmisleno
        optimizer.zero_grad()
        
        # Forward pass
        # podaci -> model -> predikcija
        logits = model(batch_X)
        
        # Calculate loss
        # usporedba predikcije i GT klase da dobijemo loss
        loss = criterion(logits, batch_y)
        
        # Backward pass
        # greška se propagira unazad
        # računaju se gradijenti i prilagođavaju neuroni koji su doprinjeli greški
        loss.backward()
        
        # Update model parameters
        # update parametara i kretanje u novi korak treninga
        optimizer.step()
        
        # --- Track Metrics ---
        # zbraja ukupne dosadašnje pogreške za dobit ukupni loss
        running_loss += loss.item() * batch_X.size(0)

        # traži predikciju s najvećim scoremom u score vektoru
        _, predictions = torch.max(logits, dim=1)
        # zbraja sve točne predikcije
        correct_predictions += (predictions == batch_y).sum().item()
        # zbraja sve predikcije generalno
        total_samples += batch_y.size(0)
        
    # Calculate epoch metrics
    epoch_loss = running_loss / total_samples
    epoch_accuracy = (correct_predictions / total_samples) * 100
    
    print(f"Epoch [{epoch+1}/{epochs}] -> Loss: {epoch_loss:.4f} | Accuracy: {epoch_accuracy:.2f}%")

print("\nTraining Complete!")
