from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional,List
# EMAIL_USER       = os.getenv("EMAIL_USER")
# OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# AUTBOUND_API_KEY = os.getenv("AUTBOUND_API_KEY")
# GITHUB_TOKEN     = os.getenv("GITHUB_TOKEN")
# RESEND_API_KEY   = os.getenv("RESEND_API_KEY")
# RESEND_SENDER    = os.getenv("RESEND_SENDER") 
# RESUME_LINK      = os.getenv("RESUME_LINK")
# GOOGLE_CREDS_PATH = os.getenv("GOOGLE_CREDS_PATH")
# SHEET_NAME       = os.getenv("SHEET_NAME")
# ALLOWED_ORIGINS  = os.getenv("ALLOWED_ORIGINS", "https://www.mohammed-karab.rest").split(",")

class APIConfig(BaseSettings):
    """
    Contains all the API Of the tools used in the application.
    """
    openrouter_api_key : str = Field(
        default= " ",
        validation_alias="OPENROUTER_API_KEY"
    )
    google_api_key: Optional[str] = Field(
        default= None,
        validation_alias= "GOOGLE_API_KEY"
    )
    google_cred_path: Optional[str]= Field(
        default="/path/to/service_account.json ",
        validation_alias="GOOGLE_CREDS_PATH"
    )
    sheet_name : str = Field(
        default= "portfoliolog ",
        validation_alias="SHEET_NAME"
    )

class EmailAPI(BaseSettings):
    """
    All the credentials related to the Gmail app 
    """
    email_host : Optional[str]= Field(
        default="smtp.gmail.com",
        validation_alias="EMAIL_HOST"
    )
    email_port : Optional[int] = Field(
        default=587,
        validation_alias="EMAIL_PORT"
    )
    email_user : Optional[str]= Field(
        default="yourgmail@gmail.com",
        validation_alias="EMAIL_USER"
    )
    email_pass : Optional[str] = Field(
        default=None,
        validation_alias="EMAIL_PASS"    
    )
    
        
class SocialAPI(BaseSettings):
    autbound_api_key : Optional[str] = Field(
        default=None,
        validation_alias="AUTBOUND_API_KEY"
    )
    github_token : Optional[str]= Field(
        default=None,
        validation_alias="GITHUB_TOKEN"
    )
    
class ResendAPI(BaseSettings):
    resend_api_key : str = Field(
        default= " ",
        validation_alias="RESEND_API_KEY"
    )
    resend_sender : str = Field(
        default=" ",
        validation_alias= "RESEND_SENDER"
    )



class Settings(BaseSettings):
    model_config={
        "env_file" : ".env",
        "env_file_encoding" : "utf-8",
        "env_ignore_empty":False,
        "extra":"ignore",
        "case_sensitive" : False        
    }
    
    allowed_hosts: List[str] = Field(
        default=["*"], validation_alias="ALLOWED_HOSTS", description="Allowed hosts for CORS"
    )
    api : APIConfig= Field(default_factory=APIConfig)
    email : EmailAPI = Field(default_factory=EmailAPI)
    social : SocialAPI = Field(default_factory=SocialAPI)
    resend : ResendAPI = Field(default_factory=ResendAPI)
    
    
    @field_validator("email", mode="before")
    @classmethod
    def email_validator(cls, v : Optional[str] ) ->Optional[str]:
        if v is None or str(v).strip =="":
            return None
        if '@' not in str(v):
            raise ValueError("Email user must have a valid email")
        return str(v).strip()
    
    
settings = Settings()

def get_settings()-> Settings:
    return settings