terraform {
  backend "gcs" {
    # REPLACE THIS with the name of the bucket you created manually
    bucket  = "hiking-trips-terraform-state-bucket"
    
    # This prefix helps you organize state if you share the bucket
    prefix  = "terraform/state"
  }
}
