import boto3

# check diff between client and resource
s3 = boto3.resource('s3')

for bucket in s3.buckets.all():
    print(bucket.name)

# 'STANDARD'|'REDUCED_REDUNDANCY'|'STANDARD_IA'|'ONEZONE_IA'|'INTELLIGENT_TIERING'|'GLACIER'|'DEEP_ARCHIVE'|'OUTPOSTS'|'GLACIER_IR'|'SNOW'
# s3.upload_file(PATH, BUCKET, KEY, ExtraArgs={'StorageClass': 'GLACIER_IR'})

# data = open('test.jpg', 'rb')
# s3.Bucket('my-bucket').put_object(Key='test.jpg', Body=data)
# use upload_file