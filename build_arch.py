import os

version = "0.9.0"
pkgname = "rory"
authors = [ "Quintin Smith <smith.quintin@protonmail.com>" ]
description = "Read midi files and play them on your keyboard"

def build_pkgbuild():
    output = """
# Maintainer: %s
pkgname=%s
pkgver=%s
pkgrel=1
epoch=
pkgdesc="%s"
arch=('x86_64')
url=""
license=('GPL')
groups=()
depends=('python>=3.8.0','wrecked_bindings>=0.1.0','apres>=0.1.0')
makedepends=()
checkdepends=()
optdepends=()
provides=()
conflicts=()
replaces=()
backup=()
options=()
install=
changelog=
source=("$pkgname-$pkgver.tar.gz")
noextract=()
validpgpkeys=()

prepare() {
    cd "$pkgname-$pkgver"
}

build() {
    cd "$pkgname-$pkgver"
}

check() {
    cd "$pkgname-$pkgver"
}

package() {
    cd "$pkgname-$pkgver"
    chmod +x ./usr/bin/%s
    mv ./usr/ "$pkgdir/"
}
""" % (
    ",".join(authors),
    pkgname,
    version,
    description,

    pkgname
)

    return output

os.mkdir(pkgname)
os.chdir(pkgname);

folder = "%s-%s" % (pkgname, version)
os.system("mkdir %s/usr/lib/%s -p" % (folder, pkgname))
os.system("mkdir %s/usr/bin/ -p" % folder)

os.system("cp ../src/* %s/usr/lib/%s/ -r" % (folder, pkgname))

with open("%s/usr/bin/%s" % (folder, pkgname), "w") as fp:
    fp.write("""
        export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/lib/%s
        /usr/lib/%s/main.py "$@"
    """ % (pkgname, pkgname))

os.system("tar --create --file \"%s.tar.gz\" %s" % (folder, folder))
os.system("rm \"%s\" -rf" % folder)

with open("PKGBUILD", "w") as fp:
    fp.write(build_pkgbuild())
os.system("makepkg -g -f -p PKGBUILD >> PKGBUILD")

os.system("rm src -rf")

os.chdir("../")
os.system("tar --create --file \"%s-dist.tar.gz\" %s/*" % (folder, pkgname))
os.system("rm %s -rf" % pkgname)
