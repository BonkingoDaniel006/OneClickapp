from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

a = "200600"
hash_a= generate_password_hash(a)
print(a)
print(f"voici la variable a completement hashée: {hash_a}")