"""Class implementation to push logs to AWS"""
import logging
import json
import boto3

logger = logging.getLogger("KinesisFirehose")


class DeliveryStreamHandler(logging.StreamHandler):
    """Class that handdle log pushing to AWS"""

    def __init__(self, configyml):
        # By default, logging.StreamHandler uses sys.stderr if stream parameter is not specified
        logging.StreamHandler.__init__(self, configyml)

        self.boto = boto3.Session(
            region_name=configyml["region_name"],
            aws_access_key_id=configyml["aws_access_key_id"],
            aws_secret_access_key=configyml["aws_secret_access_key"],
        )
        self.__firehose = None
        self.__stream_buffer = {}
        self.__delivery_stream_name = configyml["delivery_stream_name"]

    def emit(self, record):
        if self.__firehose is None:
            self.__firehose = self.boto.client("firehose")

        json_data = {}
        for attr in filter(lambda attr: not attr.endswith("__"), dir(record)):
            if attr in ["asctime", "levelName", "message"]:
                json_data[attr] = getattr(record, attr)
            if attr in ["feed"]:
                json_data[attr] = getattr(record, attr)[0]

        if "levelname" in json_data:
            json_data["severity"] = json_data["levelname"]
        else:
            json_data["severity"] = "severity"

        msg = json.loads(self.format(record))

        if "end_color" in msg:
            del msg["end_color"]

        if "level_color" in msg:
            del msg["level_color"]

        msg = json.dumps(msg)

        try:
            if self.__firehose:
                self.__stream_buffer["Data"] = msg.encode(
                    encoding="UTF-8", errors="strict"
                )

            else:
                stream = self.stream
                stream.write(msg)
                stream.write(self.terminator)
            self.flush()
        except Exception as exc:
            self.handleError(record)

    def flush(self):
        self.acquire()

        try:
            if self.__firehose and self.__stream_buffer:
                self.__firehose.put_record(
                    DeliveryStreamName=self.__delivery_stream_name,
                    Record=self.__stream_buffer,
                )
                self.__stream_buffer.clear()
        except Exception as exc:
            # logger.info(repr(exc))
            pass
        finally:
            if self.stream and hasattr(self.stream, "flush"):
                self.stream.flush()
            self.release()
