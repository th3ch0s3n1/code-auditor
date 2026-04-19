"""Sample Django models with intentional issues."""
from django.db import models


class Article(models.Model):
    title = models.CharField(max_length=200, null=True)   # null=True on CharField
    body = models.TextField(null=True)
    author = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    # Missing __str__ method


class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    text = models.TextField()

    def __str__(self):
        return self.text[:50]
