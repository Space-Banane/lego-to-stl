# LEGO Set to STL Converter

Convert LEGO sets to 3D-printable STL files automatically. Enter a set number, and the system fetches parts data from Rebrickable, converts LDraw files to STL format, and provides organized downloads with color information.


## Installation using Docker (On Linux)
1. Clone the repository:
```bash
git clone https://github.com/Space-Banane/lego-to-stl.git
cd lego-to-stl
```

1.2 Download LDraw
```bash
wget https://library.ldraw.org/library/updates/complete.zip
# This may take a while
unzip complete.zip
rm complete.zip
```

1.3 Download Ldraw2STL
```bash
git clone https://github.com/kristov/ldraw2stl.git
```

1.3 Download Datasets
```bash
wget https://cdn.rebrickable.com/media/downloads/parts.csv.zip
wget https://cdn.rebrickable.com/media/downloads/colors.csv.zip
wget https://cdn.rebrickable.com/media/downloads/sets.csv.zip
unzip parts.csv.zip
unzip colors.csv.zip
unzip sets.csv.zip
rm parts.csv.zip colors.csv.zip sets.csv.zip
```

2. Create a `.env` file based on the example and add your Rebrickable API key:
```bash
cp .env.example .env
# Edit .env to add your API key
nano .env
```

3. Build and run the Docker container:
```bash
docker-compose up --build -d
```

4. Access the application at `http://localhost:5000`.

## WARNING
This project has NO authentication, nor rate limiting. Do NOT expose it to the internet without adding proper security measures.

## Information
i am NOT affiliated with Rebrickable, LDraw, or The LEGO Group. This project is for educational purposes only.

## License
This project is licensed under the MIT License.