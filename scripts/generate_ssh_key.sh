PRIVATE_FILE="id_rsa"
PRIVATE_FILE_TEMP="id_rsa_temp"
PUBLIC_FILE="id_rsa.pub"
PUBLIC_FILE_TEMP="id_rsa_temp.pub"

cd ~/.ssh

if [ -f $PRIVATE_FILE_TEMP ]; then
    rm -f $PRIVATE_FILE_TEMP
fi

if [ -f $PUBLIC_FILE_TEMP ]; then
    rm -f $PUBLIC_FILE_TEMP
fi

if [ -f $PRIVATE_FILE ]; then
    mv $PRIVATE_FILE $PRIVATE_FILE_TEMP
fi

if [ -f $PUBLIC_FILE ]; then
    mv $PUBLIC_FILE $PUBLIC_FILE_TEMP
fi

ssh-keygen -t rsa -b 4096 -C $1 -f $PRIVATE_FILE -N """"
