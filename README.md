
# lambda-maxmind-downloader

This lambda function is designed to download files from maxmind and store
them in an s3 bucket.

![architecture-diagram](../master/images/architecture.png)

## Development

### Pre-requisites
- pipenv - for dependency management
- pyenv - for selecting python version or python 3.6

### Running tests
```
make test # This will run the unittests
make test-all # This will run the format/unit/safety tests
```

## Usage

For this function to work you would need a maxmind license as well
as an s3 bucket that this lambda can store its content in and is accessible from the lambda

### Maxmind data bucket
- Setup an s3 bucket for objects to exists in this should be a private bucket by default


### Define a maxmind lambda function

This function accesses the maxmind services and retrieves the required files it then uploads these to the s3 bucket we have defined

The function should call the ```maxmind.handler``` method

#### Environment Variables

- MAXMIND_LICENSE - the license used to access maxmind
- MAXMIND_S3_BUCKET - the bucket to store maxmind files

There are a few other environment variables which can be set but, however they have sensible defaults

#### Lambda policy

The policy for the lambda should allow it to at minimum access the s3 bucket for storing

```buildoutcfg
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject"
            ],
            "Resource": [
              "arn:aws:s3:::<bucket-name>/**"
            ]
        }    
    ]
}
```

#### Cloudwatch event rule

To ensure this is kept up to date we need to create a cloudwatch event rule
We also need to ensure the lambda function allows access from the cloudwatch event

### License

This code is open source software licensed under the [Apache 2.0 License]("http://www.apache.org/licenses/LICENSE-2.0.html").
