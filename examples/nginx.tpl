{% macro upstream(name, nodes) -%}
    upstream {{ name }} {
    {% for node in nodes %}
        server {{ node.addr }}:{{ node.port }} weight={{ node.weight }};
    {% endfor %}
    }
{%- endmacro %}

{% for proxy_detail in proxy_details %}
    {{ upstream(proxy_detail.name, proxy_detail.nodes) }}
    {% for proxy_group in proxy_detail.nodes|groupby('proto') %}
    {% if proxy_group.grouper == 'http' %}
    server {
        server_name {{ proxy_detail.name }};
        listen 80;
        location / {
            proxy_pass http://{{ proxy_detail.name }};
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forward-For $remote_addr;
        }
    }
    {% else %}
    server {
        server_name {{ proxy_detail.name }};
        listen 443;
        ssl on;
        location / {
            proxy_pass http://{{ proxy_detail.name }};
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forward-For $remote_addr;
        }
    }
    {% endif %}
    {% endfor %}
{% endfor %}
# This is just an invalid value which will never trigger on a real hostname.
server {
    server_name _;
    listen 80;
    return 503;
}
