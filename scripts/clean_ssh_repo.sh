PRIVATE_FILE="id_rsa"
PRIVATE_FILE_TEMP="id_rsa_temp"
NEW_PRIVATE_FILE=$1
PUBLIC_FILE="id_rsa.pub"
PUBLIC_FILE_TEMP="id_rsa_temp.pub"
NEW_PUBLIC_FILE=$1".pub"

cd ~/.ssh

mv $PRIVATE_FILE $NEW_PRIVATE_FILE
mv $PUBLIC_FILE $NEW_PUBLIC_FILE

if [ -f $PRIVATE_FILE_TEMP ]; then
    mv $PRIVATE_FILE_TEMP $PRIVATE_FILE
    rm -f $PRIVATE_FILE_TEMP
fi

if [ -f $PUBLIC_FILE_TEMP ]; then
    mv $PUBLIC_FILE_TEMP $PUBLIC_FILE
    rm -f $PUBLIC_FILE_TEMP
fi

{
    echo ''
    echo 'Host '$2
    echo '  HostName github.com'
    echo '  User git'
    echo '  IdentityFile ~/.ssh/'$1
    echo '  IdentitiesOnly yes'
} >> config
